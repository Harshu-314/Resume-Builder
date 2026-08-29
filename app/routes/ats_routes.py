from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db, limiter
from app.models import Resume, User
from app.services.ats_service import check_ats_score
from app.utils import error_response, success_response

ats_bp = Blueprint("ats", __name__, url_prefix="/api/ats")


@ats_bp.route("/check/<resume_id>", methods=["POST"])
@jwt_required()
@limiter.limit("30 per hour")
def check_resume(resume_id):
    """
    Body (optional): { "job_description": "paste target JD here for keyword matching" }
    Enforces the free-plan ATS check limit (Premium = unlimited, per the PRD).
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return error_response("Your account could not be found. Please log in again.", 401)

    resume = Resume.query.filter_by(id=resume_id, user_id=user_id).first()
    if not resume:
        return error_response("Resume not found.", 404)

    if user.plan != "premium" and user.ats_checks_used >= User.FREE_ATS_CHECK_LIMIT:
        return error_response(
            "Free plan ATS check limit reached. Upgrade to Premium for unlimited checks.",
            status=402,
        )

    data = request.get_json(silent=True) or {}
    job_description = data.get("job_description", resume.target_job_description or "")

    result = check_ats_score(resume.get_content(), job_description)

    resume.ats_score = result["score"]
    resume.set_ats_feedback(result)
    if job_description and not resume.target_job_description:
        resume.target_job_description = job_description

    if user.plan != "premium":
        user.ats_checks_used += 1

    db.session.commit()

    return success_response({
        "ats_result": result,
        "checks_remaining": user.ats_checks_remaining(),
    })
