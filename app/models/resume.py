import json
import uuid
from datetime import datetime
from app.extensions import db


def gen_uuid():
    return str(uuid.uuid4())


class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)

    title = db.Column(db.String(150), nullable=False, default="Untitled Resume")
    template_id = db.Column(db.String(50), nullable=False, default="minimal")

    # Structured resume content stored as JSON text:
    # { personal: {...}, summary: "", experience: [...], education: [...],
    #   skills: [...], projects: [...], certifications: [...] }
    content_json = db.Column(db.Text, nullable=False, default="{}")

    ats_score = db.Column(db.Integer, nullable=True)
    ats_feedback_json = db.Column(db.Text, nullable=True)

    target_job_title = db.Column(db.String(150), nullable=True)
    target_job_description = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_content(self):
        try:
            return json.loads(self.content_json or "{}")
        except json.JSONDecodeError:
            return {}

    def set_content(self, content: dict):
        self.content_json = json.dumps(content)

    def get_ats_feedback(self):
        if not self.ats_feedback_json:
            return None
        try:
            return json.loads(self.ats_feedback_json)
        except json.JSONDecodeError:
            return None

    def set_ats_feedback(self, feedback: dict):
        self.ats_feedback_json = json.dumps(feedback)

    def to_dict(self, include_content=True):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "template_id": self.template_id,
            "ats_score": self.ats_score,
            "ats_feedback": self.get_ats_feedback(),
            "target_job_title": self.target_job_title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_content:
            data["content"] = self.get_content()
        return data
