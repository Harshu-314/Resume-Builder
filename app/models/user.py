import uuid
from datetime import datetime
from app.extensions import db


def gen_uuid():
    return str(uuid.uuid4())


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    # Nullable because Google-signed-up users have no local password.
    password_hash = db.Column(db.String(255), nullable=True)

    auth_provider = db.Column(db.String(20), nullable=False, default="password")  # password | google | github | linkedin
    google_id = db.Column(db.String(64), unique=True, nullable=True, index=True)
    github_id = db.Column(db.String(64), unique=True, nullable=True, index=True)
    linkedin_id = db.Column(db.String(64), unique=True, nullable=True, index=True)

    plan = db.Column(db.String(20), nullable=False, default="free")  # free | premium
    ats_checks_used = db.Column(db.Integer, nullable=False, default=0)

    # --- Email verification (OTP sent on signup) ---
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    otp_hash = db.Column(db.String(255), nullable=True)
    otp_expires_at = db.Column(db.DateTime, nullable=True)
    otp_attempts = db.Column(db.Integer, nullable=False, default=0)
    otp_last_sent_at = db.Column(db.DateTime, nullable=True)

    # --- Forgot-password reset (separate OTP fields so a pending signup
    # verification and a pending password reset never collide) ---
    reset_otp_hash = db.Column(db.String(255), nullable=True)
    reset_otp_expires_at = db.Column(db.DateTime, nullable=True)
    reset_otp_attempts = db.Column(db.Integer, nullable=False, default=0)
    reset_otp_last_sent_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resumes = db.relationship("Resume", backref="owner", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "plan": self.plan,
            "auth_provider": self.auth_provider,
            "ats_checks_used": self.ats_checks_used,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    FREE_ATS_CHECK_LIMIT = 3

    def ats_checks_remaining(self):
        if self.plan == "premium":
            return None  # unlimited
        return max(0, self.FREE_ATS_CHECK_LIMIT - self.ats_checks_used)
