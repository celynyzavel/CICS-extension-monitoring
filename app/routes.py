from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from datetime import datetime

from app import db, oauth
from app.models import User, TechnologyTransfer as TechnologyTransfer_model

main = Blueprint("main", __name__)


@main.app_context_processor
def inject_flagged_technologies():

    flagged_technologies = []

    if current_user.is_authenticated and current_user.role == "COORDINATOR":
        flagged_technologies = [
            technology
            for technology in TechnologyTransfer_model.query.order_by(
                TechnologyTransfer_model.deployment_date.asc()
            ).all()
            if technology.needs_update
        ]

    return dict(flagged_technologies=flagged_technologies)


@main.route("/")
def home():
    return redirect(url_for("main.login"))

@main.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("main.index"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@main.route("/login/google")
def google_login():
    redirect_uri = url_for("main.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@main.route("/login/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()

    user_info = token.get("userinfo")

    if not user_info:
        flash("Could not get your Google account information.", "danger")
        return redirect(url_for("main.login"))

    email = user_info.get("email")

    if not email:
        flash("Google did not provide an email address.", "danger")
        return redirect(url_for("main.login"))

    user = User.query.filter_by(email=email).first()

    if not user:
        flash(
            "Your Google account is not registered or approved for this system.",
            "danger"
        )
        return redirect(url_for("main.login"))

    login_user(user)

    return redirect(url_for("main.index"))


@main.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))


@main.route("/home")
@login_required
def index():

    if current_user.role == "FACULTY":
        return render_template("HomePage_Faculty.html")

    elif current_user.role == "COORDINATOR":
        return render_template("HomePage_Coordinator.html")

    elif current_user.role == "DEAN":
        return render_template("HomePage-Dean.html")

    return "Invalid user role."

@main.route("/users")
@login_required
def users():

    if current_user.role != "COORDINATOR":
        return "Unauthorized", 403

    users = User.query.all()

    return render_template("users.html", users=users)


@main.route("/users/add", methods=["GET", "POST"])
@login_required
def add_user():

    if current_user.role != "COORDINATOR":
        return "Unauthorized", 403

    if request.method == "POST":

        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already exists.", "danger")
            return redirect(url_for("main.add_user"))


        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("User created successfully.", "success")

        return redirect(url_for("main.users"))

    return render_template("add_user.html")

VALID_ROLES = ("FACULTY", "COORDINATOR", "DEAN")


@main.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):

    if current_user.role != "COORDINATOR":
        return "Unauthorized", 403

    user = User.query.get_or_404(user_id)

    if request.method == "POST":

        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        if role not in VALID_ROLES:
            flash("Please select a valid role.", "danger")
            return redirect(url_for("main.edit_user", user_id=user.id))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user and existing_user.id != user.id:
            flash("Email already exists.", "danger")
            return redirect(url_for("main.edit_user", user_id=user.id))

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.role = role

        if password:
            user.set_password(password)

        db.session.commit()

        flash("User updated successfully.", "success")

        return redirect(url_for("main.users"))

    return render_template("edit_user.html", user=user)


@main.route("/users/delete/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):

    if current_user.role != "COORDINATOR":
        return "Unauthorized", 403

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("main.users"))

    db.session.delete(user)
    db.session.commit()

    flash("User deleted successfully.", "success")

    return redirect(url_for("main.users"))

@main.route("/technology-transfer")
@login_required
def TechnologyTransfer():

    if current_user.role != "COORDINATOR":
        flash(
            "Only the Extension Coordinator can manage technology transfer records.",
            "danger"
        )
        return redirect(url_for("main.index"))

    technologies = (
        TechnologyTransfer_model.query
        .order_by(TechnologyTransfer_model.deployment_date.desc())
        .all()
    )

    return render_template(
        "TechnologyTransfer.html",
        technologies=technologies
    )


@main.route("/technology-transfer/add", methods=["GET", "POST"])
@login_required
def TechnologyTransfer_add():

    if current_user.role != "COORDINATOR":
        flash(
            "Only the Extension Coordinator can manage technology transfer records.",
            "danger"
        )
        return redirect(url_for("main.index"))

    if request.method == "POST":
        system_name = request.form.get("system_name")
        program = request.form.get("program")
        deployment_date = request.form.get("deployment_date")
        system_type = request.form.get("system_type")
        usage_status = request.form.get("usage_status")
        user_trained = request.form.get("user_trained")
        partner_institution = request.form.get("partner_institution")
        description = request.form.get("description")

        technology = TechnologyTransfer_model(
            user_id=current_user.id,
            system_name=system_name,
            system_type=system_type,
            program=program,
            deployment_date=datetime.strptime(
                deployment_date,
                "%Y-%m-%d"
            ).date(),
            partner_institution=partner_institution,
            user_trained=int(user_trained) if user_trained else 0,
            usage_status=usage_status,
            description=description
        )

        db.session.add(technology)
        db.session.commit()

        flash(
            "Technology transfer record added successfully.",
            "success"
        )

        return redirect(
            url_for("main.TechnologyTransfer")
        )

    return render_template("TechnologyTransfer_add.html")


@main.route(
    "/technology-transfer/edit/<int:technology_id>",
    methods=["GET", "POST"]
)
@login_required
def TechnologyTransfer_edit(technology_id):

    if current_user.role != "COORDINATOR":
        flash(
            "Only the Extension Coordinator can manage technology transfer records.",
            "danger"
        )
        return redirect(url_for("main.index"))

    technology = TechnologyTransfer_model.query.get_or_404(technology_id)

    if request.method == "POST":
        technology.system_name = request.form.get("system_name")
        technology.system_type = request.form.get("system_type")
        if technology.system_type == 'Other':
            technology.system_type = request.form.get('other_system_type')   
        technology.program = request.form.get("program")
        deployment_date = request.form.get("deployment_date")
        technology.deployment_date = datetime.strptime(
            deployment_date,
            "%Y-%m-%d"
        ).date()

        technology.partner_institution = request.form.get(
            "partner_institution"
        )

        user_trained = request.form.get("user_trained")
        technology.user_trained = int(user_trained) if user_trained else 0

        technology.usage_status = request.form.get("usage_status")

        technology.description = request.form.get("description")

        db.session.commit()

        flash(
            "Technology transfer record updated successfully.",
            "success"
        )

        return redirect(url_for("main.TechnologyTransfer"))

    return render_template(
        "TechnologyTransfer_edit.html",
        technology=technology
    )


@main.route(
    "/technology-transfer/delete/<int:technology_id>",
    methods=["POST"]
)
@login_required
def delete_technology_transfer(technology_id):

    if current_user.role != "COORDINATOR":
        flash(
            "Only the Extension Coordinator can manage technology transfer records.",
            "danger"
        )
        return redirect(url_for("main.index"))

    technology = TechnologyTransfer_model.query.get_or_404(technology_id)

    db.session.delete(technology)
    db.session.commit()

    flash(
        "Technology transfer record deleted successfully.",
        "success"
    )

    return redirect(url_for("main.TechnologyTransfer"))