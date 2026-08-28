from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db, limiter
from app.models import Resume, User
from app.services.resume_ai_service import (
    generate_resume_content,
    improve_bullet_points,
    generate_advisor_suggestions,
    generate_cover_letter_snippet,
    generate_recruiter_chat_reply,
    generate_recruiter_analysis,
)
from app.services.ai_service import AIServiceError
from app.services.ats_service import check_ats_score
from app.utils import error_response, success_response

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")

# Sensible input caps for the AI Recruiter Assistant feature (job descriptions
# and chat messages/history are user-pasted free text sent straight into an
# AI prompt, so keep them bounded).
MAX_JOB_DESCRIPTION_LENGTH = 8000
MAX_CHAT_MESSAGE_LENGTH = 2000
MAX_CHAT_HISTORY_MESSAGES = 12


@ai_bp.route("/generate-resume", methods=["POST"])
@jwt_required()
@limiter.limit("15 per hour")
def generate_resume():
    """
    Body: { "profile": {...guided Q&A answers...}, "target_job_title": "...",
            "resume_id": "optional - save straight into this resume" }
    """
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    profile = data.get("profile")
    if not profile:
        return error_response("`profile` (Q&A answers) is required.")

    target_job_title = data.get("target_job_title", "")

    try:
        content = generate_resume_content(profile, target_job_title)
    except AIServiceError as e:
        return error_response(str(e), 502)

    resume_id = data.get("resume_id")
    if resume_id:
        resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()
        if not resume:
            return error_response("Resume not found.", 404)
        resume.set_content(content)
        if target_job_title:
            resume.target_job_title = target_job_title
        db.session.commit()
        return success_response({"resume": resume.to_dict()}, message="Resume generated and saved.")

    return success_response({"content": content}, message="Resume content generated.")


@ai_bp.route("/improve-bullets", methods=["POST"])
@jwt_required()
@limiter.limit("30 per hour")
def improve_bullets():
    """Body: { "bullets": ["..."], "role_context": "Software Engineer at X" }"""
    data = request.get_json(silent=True) or {}
    bullets = data.get("bullets")
    if not bullets or not isinstance(bullets, list):
        return error_response("`bullets` must be a non-empty list of strings.")

    try:
        improved = improve_bullet_points(bullets, data.get("role_context", ""))
    except AIServiceError as e:
        return error_response(str(e), 502)

    return success_response({"bullets": improved})


@ai_bp.route("/advisor/<resume_id>", methods=["POST"])
@jwt_required()
@limiter.limit("15 per hour")
def advisor(resume_id):
    """AI Resume Advisor - qualitative suggestions on a saved resume. Premium feature."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return error_response("Your account could not be found. Please log in again.", 401)
    if user.plan != "premium":
        return error_response("Recruiter AI Advisor is a Premium feature.", 402)

    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()
    if not resume:
        return error_response("Resume not found.", 404)

    try:
        feedback = generate_advisor_suggestions(resume.get_content(), resume.target_job_title or "")
    except AIServiceError as e:
        return error_response(str(e), 502)

    return success_response({"advisor_feedback": feedback})


@ai_bp.route("/cover-letter/<resume_id>", methods=["POST"])
@jwt_required()
@limiter.limit("10 per hour")
def cover_letter(resume_id):
    """Future feature (AI Cover Letter Generator) - included but not required for MVP."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return error_response("Your account could not be found. Please log in again.", 401)
    if user.plan != "premium":
        return error_response("Cover letter generation is a Premium feature.", 402)

    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()
    if not resume:
        return error_response("Resume not found.", 404)

    data = request.get_json(silent=True) or {}
    job_description = data.get("job_description", "")
    if not job_description.strip():
        return error_response("`job_description` is required.")

    try:
        snippet = generate_cover_letter_snippet(resume.get_content(), job_description)
    except AIServiceError as e:
        return error_response(str(e), 502)

    return success_response({"cover_letter_opening": snippet})


@ai_bp.route("/recruiter-analysis/<resume_id>", methods=["POST"])
@jwt_required()
@limiter.limit("15 per hour")
def recruiter_analysis(resume_id):
    """
    AI Recruiter Assistant - Resume vs Job Description analysis. Premium
    feature, consistent with the Advisor and Cover Letter endpoints above.
    Reuses the deterministic ATS engine for the score/keyword matching and
    layers an AI-generated recruiter narrative on top of it.
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return error_response("Your account could not be found. Please log in again.", 401)
    if user.plan != "premium":
        return error_response("AI Recruiter Assistant analysis is a Premium feature.", 402)

    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()
    if not resume:
        return error_response("Resume not found.", 404)

    data = request.get_json(silent=True) or {}
    job_description = (data.get("job_description") or "").strip()
    if not job_description:
        return error_response("`job_description` is required.")
    if len(job_description) > MAX_JOB_DESCRIPTION_LENGTH:
        return error_response(f"`job_description` is too long (max {MAX_JOB_DESCRIPTION_LENGTH} characters).")

    content = resume.get_content()
    ats_result = check_ats_score(content, job_description)

    try:
        analysis = generate_recruiter_analysis(content, job_description, ats_result)
    except AIServiceError as e:
        return error_response(str(e), 502)

    # Keep the resume's stored ATS score/feedback and job description in
    # sync with what the dedicated ATS Checker tab would compute.
    resume.ats_score = ats_result["score"]
    resume.set_ats_feedback(ats_result)
    if not resume.target_job_description:
        resume.target_job_description = job_description
    db.session.commit()

    return success_response({"analysis": analysis})


@ai_bp.route("/recruiter-chat/<resume_id>", methods=["POST"])
@jwt_required()
@limiter.limit("40 per hour")
def recruiter_chat(resume_id):
    """
    AI Recruiter Assistant - conversational chat grounded in the candidate's
    saved resume and the pasted job description. Premium feature.

    Body: { "job_description": "...", "message": "...",
            "conversation_history": [{"role": "user"|"assistant", "content": "..."}] }
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return error_response("Your account could not be found. Please log in again.", 401)
    if user.plan != "premium":
        return error_response("AI Recruiter Assistant chat is a Premium feature.", 402)

    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()
    if not resume:
        return error_response("Resume not found.", 404)

    data = request.get_json(silent=True) or {}
    job_description = (data.get("job_description") or "").strip()
    message = (data.get("message") or "").strip()
    conversation_history = data.get("conversation_history")

    if not job_description:
        return error_response("`job_description` is required.")
    if not message:
        return error_response("`message` is required.")
    if len(job_description) > MAX_JOB_DESCRIPTION_LENGTH:
        return error_response(f"`job_description` is too long (max {MAX_JOB_DESCRIPTION_LENGTH} characters).")
    if len(message) > MAX_CHAT_MESSAGE_LENGTH:
        return error_response(f"`message` is too long (max {MAX_CHAT_MESSAGE_LENGTH} characters).")
    if conversation_history is not None and not isinstance(conversation_history, list):
        return error_response("`conversation_history` must be a list.")

    # Defensively trim + sanitize the client-supplied history regardless of
    # what the frontend sends, before it ever reaches the AI prompt.
    safe_history = []
    for item in (conversation_history or [])[-MAX_CHAT_HISTORY_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role") if item.get("role") in ("user", "assistant") else "user"
        text = str(item.get("content", ""))[:MAX_CHAT_MESSAGE_LENGTH]
        if text:
            safe_history.append({"role": role, "content": text})

    try:
        reply = generate_recruiter_chat_reply(resume.get_content(), job_description, safe_history, message)
    except AIServiceError as e:
        return error_response(str(e), 502)

    if not resume.target_job_description:
        resume.target_job_description = job_description
        db.session.commit()

    return success_response({"reply": reply})
