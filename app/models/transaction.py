import uuid
from datetime import datetime
from app.extensions import db


def gen_uuid():
    return str(uuid.uuid4())


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    utr = db.Column(db.String(64), unique=True, nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False, default=20.0)
    method = db.Column(db.String(50), nullable=False, default="UPI")
    status = db.Column(db.String(20), nullable=False, default="SUCCESS")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "utr": self.utr,
            "amount": self.amount,
            "method": self.method,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
