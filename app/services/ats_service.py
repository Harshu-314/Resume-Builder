"""
ATS Checker service.

Rule-based ATS scoring engine.
Works without AI and is resilient to different resume JSON structures.
"""

import re

ACTION_VERBS = {
    "led", "built", "created", "designed", "developed", "implemented",
    "managed", "launched", "improved", "increased", "reduced",
    "optimized", "automated", "architected", "delivered", "drove",
    "spearheaded", "streamlined", "achieved", "generated",
    "negotiated", "mentored", "coordinated", "analyzed",
    "engineered", "founded", "scaled", "resolved",
    "trained", "presented", "researched",
}

WEAK_PHRASES = {
    "responsible for",
    "worked on",
    "helped with",
    "duties included",
    "team player",
    "hard worker",
    "detail oriented",
    "go-getter",
}

STOPWORDS = {
    "the","a","an","and","or","of","to","in","for","with",
    "on","at","by","from","as","is","are","be","this",
    "that","will","we","you","our","your","using",
}


def _tokenize(text: str):
    return set(re.findall(r"[a-zA-Z][a-zA-Z0-9+.#]{1,}", text.lower())) - STOPWORDS


def _flatten_resume_text(content: dict):
    """
    Safely flattens any resume structure into plain text.
    Supports nested dictionaries/lists automatically.
    """

    parts = []

    def walk(value):
        if value is None:
            return

        if isinstance(value, str):
            if value.strip():
                parts.append(value.strip())

        elif isinstance(value, list):
            for item in value:
                walk(item)

        elif isinstance(value, dict):
            for v in value.values():
                walk(v)

        else:
            parts.append(str(value))

    walk(content)

    return " ".join(parts)


def _collect_bullets(content):

    bullets = []

    for exp in content.get("experience", []):

        data = exp.get("description") or exp.get("bullets", [])

        if isinstance(data, list):
            bullets.extend([str(x) for x in data])

        elif data:
            bullets.append(str(data))

    for proj in content.get("projects", []):

        data = proj.get("description") or proj.get("bullets", [])

        if isinstance(data, list):
            bullets.extend([str(x) for x in data])

        elif data:
            bullets.append(str(data))

    return bullets


def check_ats_score(content: dict, job_description: str = ""):

    suggestions = []
    breakdown = {}

    ##################################################
    # Structure
    ##################################################

    required_sections = {
        "summary": bool(content.get("summary")),
        "experience": bool(content.get("experience")),
        "education": bool(content.get("education")),
        "skills": bool(content.get("skills")),
        "projects": bool(content.get("projects")),
    }

    structure_score = round(
        25 * sum(required_sections.values()) / len(required_sections)
    )

    breakdown["structure"] = structure_score

    for section, present in required_sections.items():
        if not present:
            suggestions.append(
                f"Add a '{section}' section - it's missing or empty."
            )

    ##################################################
    # Keyword Matching
    ##################################################

    resume_text = _flatten_resume_text(content)

    resume_tokens = _tokenize(resume_text)

    matched_keywords = []
    missing_keywords = []

    if job_description.strip():

        jd_tokens = _tokenize(job_description)

        matched = jd_tokens & resume_tokens
        missing = jd_tokens - resume_tokens

        matched_keywords = sorted(matched)

        missing_keywords = sorted(
            missing,
            key=len,
            reverse=True
        )[:15]

        ratio = len(matched) / max(len(jd_tokens), 1)

        keyword_score = round(min(ratio * 30, 30))

    else:

        keyword_score = 15

        suggestions.append(
            "Paste a target job description for a more accurate ATS score."
        )

    breakdown["keywords"] = keyword_score

    if missing_keywords:

        suggestions.append(
            "Consider adding these keywords if relevant: "
            + ", ".join(missing_keywords[:8])
        )

    ##################################################
    # Action Verbs
    ##################################################

    bullets = _collect_bullets(content)

    if bullets:

        strong = 0
        weak = 0

        for bullet in bullets:

            words = bullet.split()

            if words:

                first = words[0].lower().rstrip(",.")

                if first in ACTION_VERBS:
                    strong += 1

            for phrase in WEAK_PHRASES:

                if phrase in bullet.lower():
                    weak += 1

        ratio = strong / len(bullets)

        breakdown["action_verbs"] = round(ratio * 20)

        if ratio < 0.6:
            suggestions.append(
                "Start more bullet points with strong action verbs."
            )

        if weak:
            suggestions.append(
                f"Replace {weak} weak phrases with measurable achievements."
            )

    else:

        breakdown["action_verbs"] = 0

        suggestions.append(
            "Add bullet points to your experience and projects."
        )

    ##################################################
    # Quantification
    ##################################################

    if bullets:

        quantified = sum(
            1
            for b in bullets
            if re.search(r"\d", b)
        )

        ratio = quantified / len(bullets)

        breakdown["quantification"] = round(ratio * 15)

        if ratio < 0.4:

            suggestions.append(
                "Quantify more achievements using numbers or percentages."
            )

    else:

        breakdown["quantification"] = 0

    ##################################################
    # Formatting
    ##################################################

    formatting = 10

    skills = content.get("skills", [])

    if len(skills) < 5:

        formatting -= 2

        suggestions.append(
            "List at least 5-8 relevant skills."
        )

    long_bullets = [
        b
        for b in bullets
        if len(b.split()) > 30
    ]

    if long_bullets:

        formatting -= 3

        suggestions.append(
            "Keep bullet points concise."
        )

    breakdown["formatting"] = max(formatting, 0)

    ##################################################
    # Final Score
    ##################################################

    total = sum(breakdown.values())

    total = max(0, min(100, total))

    return {
        "score": total,
        "breakdown": breakdown,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "suggestions": suggestions,
    }