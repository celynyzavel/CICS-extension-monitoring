from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from app import db

MONITORING_PERIOD_DAYS = 182

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    def __repr__(self):
        return f"<User {self.email}>"

class TechnologyTransfer(db.Model):
    __tablename__ = "technology_transfers"

    technology_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False)
    system_name = db.Column(db.String(200), nullable=False)
    program = db.Column(db.String(200), nullable=False)
    deployment_date = db.Column(db.Date, nullable=False)
    system_type = db.Column(db.String(100), nullable=False)
    usage_status = db.Column(db.String(50), nullable=False)
    user_trained = db.Column(db.Integer, nullable=False, default=0)
    partner_institution = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user = db.relationship(
        "User",
        backref=db.backref("technology_transfers", lazy=True)
    )

    @property
    def needs_update(self):
        return date.today() >= self.deployment_date + timedelta(
            days=MONITORING_PERIOD_DAYS
        )

    def __repr__(self):
        return f"<TechnologyTransfer {self.system_name}>"
    
class Program(db.Model):
    __tablename__ = "programs"

    program_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"),nullable=False)
    program_name = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    province = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    barangay = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)

    user = db.relationship(
        "User",
        backref=db.backref("programs", lazy=True)
    )

    def __repr__(self):
        return f"<Program {self.program_name}>"