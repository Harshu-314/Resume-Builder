"""
Seeds the database with one demo user and one sample resume, so you have
something to test the frontend against immediately.

Usage:  python seed.py
"""
from app import create_app
from app.extensions import db, bcrypt
from app.models import User, Resume

app = create_app()

SAMPLE_CONTENT = {
    "personal": {
        "name": "Asha Rao",
        "email": "asha.rao@example.com",
        "phone": "+91 90000 00000",
        "location": "Hyderabad, India",
        "linkedin": "linkedin.com/in/asharao",
        "portfolio": "asharao.dev",
    },
    "summary": "Final-year CS student who has shipped 3 full-stack projects and interned "
    "as a backend developer, focused on building reliable, well-tested APIs.",
    "experience": [
        {
            "role": "Backend Developer Intern",
            "company": "TechNova Pvt Ltd",
            "duration": "May 2025 - Jul 2025",
            "bullets": [
                "Built 12 REST API endpoints used by 3 internal teams, cutting manual reporting time by 40%",
                "Reduced average API response time by 220ms by adding database indexes and query caching",
            ],
        }
    ],
    "education": [
        {
            "degree": "B.Tech in Computer Science",
            "institution": "JNTU Hyderabad",
            "duration": "2022 - 2026",
            "details": "CGPA: 8.7/10",
        }
    ],
    "skills": ["Python", "Flask", "JavaScript", "SQL", "Git", "REST APIs", "Docker"],
    "projects": [
        {
            "name": "AI Resume Builder",
            "description": "A Micro SaaS platform that generates ATS-friendly resumes using AI.",
            "bullets": ["Designed the ATS scoring engine used by 200+ beta testers"],
            "tech_stack": ["Flask", "SQLite", "Gemini API"],
        }
    ],
    "certifications": ["Google Data Analytics Certificate"],
}


def seed():
    with app.app_context():
        existing = User.query.filter_by(email="demo@resumebuilder.test").first()
        if existing:
            print("Demo user already exists - skipping seed.")
            return

        demo_user = User(
            name="Demo User",
            email="demo@resumebuilder.test",
            password_hash=bcrypt.generate_password_hash("Password123").decode("utf-8"),
            email_verified=True,  # seeded demo account skips the OTP flow
        )
        db.session.add(demo_user)
        db.session.flush()  # get demo_user.id before commit

        resume = Resume(
            user_id=demo_user.id,
            title="Asha Rao - Backend Developer",
            template_id="modern",
            target_job_title="Backend Developer",
        )
        resume.set_content(SAMPLE_CONTENT)
        db.session.add(resume)

        db.session.commit()
        print("Seeded demo user: demo@resumebuilder.test / Password123")


if __name__ == "__main__":
    seed()
