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
    capstone_title = db.Column(db.String(200),nullable=False)
    specialized_track = db.Column(db.String(100),nullable=True)
    deployment_date = db.Column(db.Date,nullable=False)
    system_type = db.Column(db.String(100),nullable=False)
    deployment_status = db.Column(db.String(50),nullable=False)
    total_users_trained = db.Column(db.Integer,nullable=False,default=0)
    partner_institution = db.Column(db.String(200),nullable=False)
    beneficiary_name = db.Column(db.String(150),nullable=True)
    beneficiary_phone_number = db.Column(db.String(30),nullable=True)
    beneficiary_position = db.Column(db.String(100),nullable=True)
    female_users_trained = db.Column( db.Integer,nullable=False,default=0)
    male_users_trained = db.Column(db.Integer,nullable=False,default=0)
    updated_at = db.Column(db.DateTime,nullable=False,default=datetime.utcnow,onupdate=datetime.utcnow)

    user = db.relationship("User",backref=db.backref("technology_transfers",lazy=True))
    
    @property
    def needs_update(self):
        return date.today() >= self.deployment_date + timedelta(
            days=MONITORING_PERIOD_DAYS
        )

    def __repr__(self):
        return f"<TechnologyTransfer {self.capstone_title}>"
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

class Project(db.Model):
    """Faculty extension project linked optionally to an extension program."""
    __tablename__ = "projects"

    project_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.program_id", ondelete="SET NULL"),
        nullable=True
    )
    project_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    involvement = db.Column(db.String(50), nullable=False, default="Support Staff")
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Planning")

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
        backref=db.backref("projects", lazy=True)
    )
    program = db.relationship(
        "Program",
        backref=db.backref("projects", lazy=True)
    )

    def __repr__(self):
        return f"<Project {self.project_name}>"


class Activity(db.Model):
    """Extension activity conducted under a program or project."""
    __tablename__ = "activities"

    activity_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.program_id", ondelete="SET NULL"),
        nullable=True
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.project_id", ondelete="SET NULL"),
        nullable=True
    )
    activity_name = db.Column(db.String(200), nullable=False)
    activity_type = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Pending")
    participants_attended = db.Column(db.Integer, nullable=False, default=0)
    participants_target = db.Column(db.Integer, nullable=False, default=0)
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
        backref=db.backref("activities", lazy=True)
    )
    program = db.relationship(
        "Program",
        backref=db.backref("activities", lazy=True)
    )
    project = db.relationship(
        "Project",
        backref=db.backref("activities", lazy=True)
    )

    @property
    def participants_display(self):
        return f"{self.participants_attended} / {self.participants_target}"

    @property
    def date_display(self):
        if self.start_date == self.end_date:
            return self.start_date.strftime("%b %d, %Y")
        return f"{self.start_date.strftime('%b %d')} – {self.end_date.strftime('%b %d, %Y')}"

    def __repr__(self):
        return f"<Activity {self.activity_name}>"


class BudgetAllocation(db.Model):
    """Overall annual budget allocated by the Extension Coordinator."""
    __tablename__ = "budget_allocations"

    budget_id = db.Column(db.Integer, primary_key=True)
    fiscal_year = db.Column(db.Integer, nullable=False, unique=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    allocated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date_allocated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default="Active")
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    allocator = db.relationship(
        "User",
        backref=db.backref("budget_allocations", lazy=True)
    )

    @property
    def is_active(self):
        return self.status == "Active"

    def __repr__(self):
        return f"<BudgetAllocation {self.fiscal_year}: {self.amount}>"


class BudgetItem(db.Model):
    """Faculty-submitted budget breakdown for an extension program/project/activity."""
    __tablename__ = "budget_items"

    budget_item_id = db.Column(db.Integer, primary_key=True)

    # Links each faculty budget item to the coordinator's annual allocation.
    # This matches the existing budget_items table in the shared database.
    budget_id = db.Column(
        db.Integer,
        db.ForeignKey("budget_allocations.budget_id"),
        nullable=False
    )

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    fiscal_year = db.Column(db.Integer, nullable=False)

    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.program_id", ondelete="SET NULL"),
        nullable=True
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.project_id", ondelete="SET NULL"),
        nullable=True
    )
    activity_id = db.Column(
        db.Integer,
        db.ForeignKey("activities.activity_id", ondelete="SET NULL"),
        nullable=True
    )

    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    allocated_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    utilized_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    supporting_document = db.Column(db.String(255), nullable=True)

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

    budget = db.relationship(
        "BudgetAllocation",
        backref=db.backref("budget_items", lazy=True)
    )

    user = db.relationship(
        "User",
        backref=db.backref("budget_items", lazy=True)
    )
    program = db.relationship(
        "Program",
        backref=db.backref("budget_items", lazy=True)
    )
    project = db.relationship(
        "Project",
        backref=db.backref("budget_items", lazy=True)
    )
    activity = db.relationship(
        "Activity",
        backref=db.backref("budget_items", lazy=True)
    )

    @property
    def remaining_amount(self):
        return self.allocated_amount - self.utilized_amount

    def __repr__(self):
        return f"<BudgetItem {self.category}: {self.allocated_amount}>"
