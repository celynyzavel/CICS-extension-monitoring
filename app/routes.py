from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from datetime import datetime
import json
from pathlib import Path

from app import db, oauth
from app.models import (
    User,
    TechnologyTransfer as TechnologyTransfer_model,
    Program as Program_model,
    Project as Project_model,
    Activity as Activity_model,
    BudgetAllocation as BudgetAllocation_model,
    BudgetItem as BudgetItem_model
)

main = Blueprint("main", __name__)

VALID_PROGRAM_STATUSES = ("Planning", "Ongoing", "Completed", "Cancelled")
VALID_PROJECT_STATUSES = ("Planning", "Ongoing", "Completed", "Cancelled")
VALID_PROJECT_INVOLVEMENTS = ("Project Leader", "Co-Implementer", "Support Staff")
VALID_ACTIVITY_STATUSES = ("Pending", "Ongoing", "Completed", "Cancelled")

LOCATIONS_DATA_DIR = Path(__file__).resolve().parent / "data"

_ph_provinces_cache = None
_ph_cities_cache = None
_ph_barangays_cache = None


def _load_location_json(filename):
    with open(LOCATIONS_DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def _get_ph_provinces():
    global _ph_provinces_cache

    if _ph_provinces_cache is None:
        _ph_provinces_cache = _load_location_json("ph_provinces.json")

    return _ph_provinces_cache


def _get_ph_cities():
    global _ph_cities_cache

    if _ph_cities_cache is None:
        _ph_cities_cache = _load_location_json("ph_cities.json")

    return _ph_cities_cache


def _get_ph_barangays():
    global _ph_barangays_cache

    if _ph_barangays_cache is None:
        _ph_barangays_cache = _load_location_json("ph_barangays.json")

    return _ph_barangays_cache

@main.route("/api/locations/provinces")
@login_required
def api_locations_provinces():
    provinces = sorted(_get_ph_provinces(), key=lambda p: p["name"])
    return jsonify(provinces)


@main.route("/api/locations/cities")
@login_required
def api_locations_cities():
    province_code = request.args.get("province_code", "")

    cities = [
        city
        for city in _get_ph_cities()
        if city["province_code"] == province_code
    ]

    cities.sort(key=lambda city: city["name"])
    return jsonify(cities)


@main.route("/api/locations/barangays")
@login_required
def api_locations_barangays():
    city_code = request.args.get("city_code", "")

    barangays = [
        barangay
        for barangay in _get_ph_barangays()
        if barangay["city_code"] == city_code
    ]

    barangays.sort(key=lambda barangay: barangay["name"])
    return jsonify(barangays)

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
        capstone_title = request.form.get("capstone_title", "").strip()
        specialized_track = request.form.get("specialized_track", "").strip()
        system_type = request.form.get("system_type", "").strip()
        other_system_type = request.form.get("other_system_type", "").strip()
        deployment_date = request.form.get("deployment_date", "").strip()
        deployment_status = request.form.get("deployment_status", "").strip()
        partner_institution = request.form.get("partner_institution", "").strip()
        beneficiary_name = request.form.get("beneficiary_name", "").strip()
        beneficiary_phone_number = request.form.get(
            "beneficiary_phone_number",
            ""
        ).strip()
        beneficiary_position = request.form.get("beneficiary_position", "").strip()

        if not all([
            capstone_title,
            specialized_track,
            system_type,
            deployment_date,
            deployment_status,
            partner_institution,
            beneficiary_name,
            beneficiary_phone_number,
            beneficiary_position
        ]):
            flash("Please complete all required fields.", "danger")
            return redirect(url_for("main.TechnologyTransfer_add"))

        if system_type == "Other":
            if not other_system_type:
                flash("Please specify the system type.", "danger")
                return redirect(url_for("main.TechnologyTransfer_add"))

            system_type = other_system_type

        if deployment_status not in ("Active", "Inactive"):
            flash("Please select a valid deployment status.", "danger")
            return redirect(url_for("main.TechnologyTransfer_add"))

        try:
            parsed_deployment_date = datetime.strptime(
                deployment_date,
                "%Y-%m-%d"
            ).date()

        except (TypeError, ValueError):
            flash("Please provide a valid deployment date.", "danger")
            return redirect(url_for("main.TechnologyTransfer_add"))

        try:
            female_users_trained = int(
                request.form.get("female_users_trained") or 0
            )

            male_users_trained = int(
                request.form.get("male_users_trained") or 0
            )

        except (TypeError, ValueError):
            flash("Users trained must be whole numbers.", "danger")
            return redirect(url_for("main.TechnologyTransfer_add"))

        if female_users_trained < 0 or male_users_trained < 0:
            flash("Users trained cannot be negative.", "danger")
            return redirect(url_for("main.TechnologyTransfer_add"))

        total_users_trained = female_users_trained + male_users_trained

        technology = TechnologyTransfer_model(
            user_id=current_user.id,
            capstone_title=capstone_title.title(),
            specialized_track=specialized_track.title(),
            system_type=system_type.title(),
            deployment_date=parsed_deployment_date,
            deployment_status=deployment_status,
            partner_institution=partner_institution.title(),
            beneficiary_name=beneficiary_name.title(),
            beneficiary_phone_number=beneficiary_phone_number,
            beneficiary_position=beneficiary_position.title(),
            female_users_trained=female_users_trained,
            male_users_trained=male_users_trained,
            total_users_trained=total_users_trained
        )

        db.session.add(technology)
        db.session.commit()

        flash("Technology transfer record added successfully.", "success")
        return redirect(url_for("main.TechnologyTransfer"))

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
        capstone_title = request.form.get("capstone_title", "").strip()
        specialized_track = request.form.get("specialized_track", "").strip()
        system_type = request.form.get("system_type", "").strip()
        other_system_type = request.form.get("other_system_type", "").strip()
        deployment_date = request.form.get("deployment_date", "").strip()
        deployment_status = request.form.get("deployment_status", "").strip()
        partner_institution = request.form.get("partner_institution", "").strip()
        beneficiary_name = request.form.get("beneficiary_name", "").strip()
        beneficiary_phone_number = request.form.get(
            "beneficiary_phone_number",
            ""
        ).strip()
        beneficiary_position = request.form.get("beneficiary_position", "").strip()

        if not all([
            capstone_title,
            specialized_track,
            system_type,
            deployment_date,
            deployment_status,
            partner_institution,
            beneficiary_name,
            beneficiary_phone_number,
            beneficiary_position
        ]):
            flash("Please complete all required fields.", "danger")
            return redirect(
                url_for(
                    "main.TechnologyTransfer_edit",
                    technology_id=technology_id
                )
            )

        if system_type == "Other":
            if not other_system_type:
                flash("Please specify the system type.", "danger")

                return redirect(
                    url_for(
                        "main.TechnologyTransfer_edit",
                        technology_id=technology_id
                    )
                )

            system_type = other_system_type

        if deployment_status not in ("Active", "Inactive"):
            flash("Please select a valid deployment status.", "danger")

            return redirect(
                url_for(
                    "main.TechnologyTransfer_edit",
                    technology_id=technology_id
                )
            )

        try:
            parsed_deployment_date = datetime.strptime(
                deployment_date,
                "%Y-%m-%d"
            ).date()

        except (TypeError, ValueError):
            flash("Please provide a valid deployment date.", "danger")

            return redirect(
                url_for(
                    "main.TechnologyTransfer_edit",
                    technology_id=technology_id
                )
            )

        try:
            female_users_trained = int(
                request.form.get("female_users_trained") or 0
            )

            male_users_trained = int(
                request.form.get("male_users_trained") or 0
            )

        except (TypeError, ValueError):
            flash("Users trained must be whole numbers.", "danger")

            return redirect(
                url_for(
                    "main.TechnologyTransfer_edit",
                    technology_id=technology_id
                )
            )

        if female_users_trained < 0 or male_users_trained < 0:
            flash("Users trained cannot be negative.", "danger")

            return redirect(
                url_for(
                    "main.TechnologyTransfer_edit",
                    technology_id=technology_id
                )
            )

        total_users_trained = female_users_trained + male_users_trained

        technology.capstone_title = capstone_title.title()
        technology.specialized_track = specialized_track.title()
        technology.system_type = system_type.title()
        technology.deployment_date = parsed_deployment_date
        technology.deployment_status = deployment_status
        technology.partner_institution = partner_institution.title()
        technology.beneficiary_name = beneficiary_name.title()
        technology.beneficiary_phone_number = beneficiary_phone_number
        technology.beneficiary_position = beneficiary_position.title()
        technology.female_users_trained = female_users_trained
        technology.male_users_trained = male_users_trained
        technology.total_users_trained = total_users_trained

        db.session.commit()

        flash("Technology transfer record updated successfully.", "success")
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

    flash("Technology transfer record deleted successfully.", "success")
    return redirect(url_for("main.TechnologyTransfer"))

@main.route("/programs")
@login_required
def Program():
    if current_user.role not in ("FACULTY", "COORDINATOR"):
        flash(
            "You are not authorized to view extension programs.",
            "danger"
        )
        return redirect(url_for("main.index"))

    if current_user.role == "FACULTY":
        programs = (
            Program_model.query
            .filter_by(user_id=current_user.id)
            .order_by(Program_model.start_date.desc())
            .all()
        )

        base_template = "base_faculty.html"

    else:
        programs = (
            Program_model.query
            .order_by(Program_model.start_date.desc())
            .all()
        )

        base_template = "base_coordinator.html"

    return render_template(
        "Program.html",
        programs=programs,
        base_template=base_template,
        can_manage=(current_user.role == "FACULTY")
    )


@main.route("/programs/add", methods=["GET", "POST"])
@login_required
def Program_add():
    if current_user.role != "FACULTY":
        flash(
            "Only the Faculty Extensionist can manage extension programs.",
            "danger"
        )
        return redirect(url_for("main.Program"))

    if request.method == "POST":
        program_name = request.form.get("program_name")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        province = request.form.get("province")
        city = request.form.get("city")
        barangay = request.form.get("barangay")
        status = request.form.get("status")
        description = request.form.get("description")

        if status not in VALID_PROGRAM_STATUSES:
            flash("Please select a valid status.", "danger")
            return redirect(url_for("main.Program_add"))

        if not (province and city and barangay):
            flash(
                "Please select a complete location "
                "(Province, City/Municipality, and Barangay).",
                "danger"
            )
            return redirect(url_for("main.Program_add"))

        program = Program_model(
            user_id=current_user.id,
            program_name=program_name,
            start_date=datetime.strptime(start_date, "%Y-%m-%d").date(),
            end_date=datetime.strptime(end_date, "%Y-%m-%d").date(),
            province=province,
            city=city,
            barangay=barangay,
            status=status,
            description=description
        )

        db.session.add(program)
        db.session.commit()

        flash("Extension program added successfully.", "success")
        return redirect(url_for("main.Program"))

    return render_template("Program_add.html")


@main.route("/programs/edit/<int:program_id>", methods=["GET", "POST"])
@login_required
def Program_edit(program_id):
    if current_user.role != "FACULTY":
        flash(
            "Only the Faculty Extensionist can manage extension programs.",
            "danger"
        )
        return redirect(url_for("main.Program"))

    program = Program_model.query.get_or_404(program_id)

    if program.user_id != current_user.id:
        flash(
            "You can only manage extension programs you created.",
            "danger"
        )
        return redirect(url_for("main.Program"))

    if request.method == "POST":
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        status = request.form.get("status")

        if status not in VALID_PROGRAM_STATUSES:
            flash("Please select a valid status.", "danger")

            return redirect(
                url_for(
                    "main.Program_edit",
                    program_id=program.program_id
                )
            )

        province = request.form.get("province")
        city = request.form.get("city")
        barangay = request.form.get("barangay")

        if not (province and city and barangay):
            flash(
                "Please select a complete location "
                "(Province, City/Municipality, and Barangay).",
                "danger"
            )

            return redirect(
                url_for(
                    "main.Program_edit",
                    program_id=program.program_id
                )
            )

        program.program_name = request.form.get("program_name")
        program.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        program.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        program.province = province
        program.city = city
        program.barangay = barangay
        program.status = status
        program.description = request.form.get("description")

        db.session.commit()

        flash("Extension program updated successfully.", "success")
        return redirect(url_for("main.Program"))

    return render_template("Program_edit.html", program=program)


@main.route("/programs/delete/<int:program_id>", methods=["POST"])
@login_required
def delete_program(program_id):
    if current_user.role != "FACULTY":
        flash(
            "Only the Faculty Extensionist can manage extension programs.",
            "danger"
        )
        return redirect(url_for("main.Program"))

    program = Program_model.query.get_or_404(program_id)

    if program.user_id != current_user.id:
        flash(
            "You can only manage extension programs you created.",
            "danger"
        )
        return redirect(url_for("main.Program"))

    db.session.delete(program)
    db.session.commit()

    flash("Extension program deleted successfully.", "success")
    return redirect(url_for("main.Program"))

@main.route("/projects")
@login_required
def Project():
    if current_user.role not in ("FACULTY", "COORDINATOR"):
        flash(
            "You are not authorized to view extension projects.",
            "danger"
        )
        return redirect(url_for("main.index"))

    if current_user.role == "FACULTY":
        projects = (
            Project_model.query
            .filter_by(user_id=current_user.id)
            .order_by(Project_model.start_date.desc())
            .all()
        )

        base_template = "base_faculty.html"

    else:
        projects = (
            Project_model.query
            .order_by(Project_model.start_date.desc())
            .all()
        )

        base_template = "base_coordinator.html"

    return render_template(
        "Project.html",
        projects=projects,
        base_template=base_template,
        can_manage=(current_user.role == "FACULTY")
    )


@main.route("/projects/add", methods=["GET", "POST"])
@login_required
def Project_add():
    if current_user.role != "FACULTY":
        flash(
            "Only the Faculty Extensionist can manage extension projects.",
            "danger"
        )
        return redirect(url_for("main.Project"))

    programs = (
        Program_model.query
        .filter_by(user_id=current_user.id)
        .order_by(Program_model.program_name.asc())
        .all()
    )

    if request.method == "POST":
        project_name = request.form.get("project_name", "").strip()
        description = request.form.get("description", "").strip()
        involvement = request.form.get("involvement")
        status = request.form.get("status")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        program_id = request.form.get("program_id") or None

        if involvement not in VALID_PROJECT_INVOLVEMENTS:
            flash("Please select a valid involvement.", "danger")
            return redirect(url_for("main.Project_add"))

        if status not in VALID_PROJECT_STATUSES:
            flash("Please select a valid project status.", "danger")
            return redirect(url_for("main.Project_add"))

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()

        except (TypeError, ValueError):
            flash("Please provide valid project dates.", "danger")
            return redirect(url_for("main.Project_add"))

        if end < start:
            flash(
                "End date cannot be earlier than the start date.",
                "danger"
            )
            return redirect(url_for("main.Project_add"))

        selected_program = None

        if program_id:
            try:
                selected_program = Program_model.query.filter_by(
                    program_id=int(program_id),
                    user_id=current_user.id
                ).first()

            except ValueError:
                selected_program = None

            if selected_program is None:
                flash("Please select a valid parent program.", "danger")
                return redirect(url_for("main.Project_add"))

        project = Project_model(
            user_id=current_user.id,
            program_id=(
                selected_program.program_id
                if selected_program
                else None
            ),
            project_name=project_name,
            description=description,
            involvement=involvement,
            start_date=start,
            end_date=end,
            status=status
        )

        db.session.add(project)
        db.session.commit()

        flash("Extension project added successfully.", "success")
        return redirect(url_for("main.Project"))

    return render_template("Project_add.html", programs=programs)


@main.route("/projects/edit/<int:project_id>", methods=["GET", "POST"])
@login_required
def Project_edit(project_id):
    if current_user.role != "FACULTY":
        flash(
            "Only the Faculty Extensionist can manage extension projects.",
            "danger"
        )
        return redirect(url_for("main.Project"))

    project = Project_model.query.get_or_404(project_id)

    if project.user_id != current_user.id:
        flash(
            "You can only manage extension projects you created.",
            "danger"
        )
        return redirect(url_for("main.Project"))

    programs = (
        Program_model.query
        .filter_by(user_id=current_user.id)
        .order_by(Program_model.program_name.asc())
        .all()
    )

    if request.method == "POST":
        program_id = request.form.get("program_id") or None
        project_name = request.form.get("project_name", "").strip()
        description = request.form.get("description", "").strip()
        involvement = request.form.get("involvement")
        status = request.form.get("status")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        if involvement not in VALID_PROJECT_INVOLVEMENTS:
            flash("Please select a valid involvement.", "danger")

            return redirect(
                url_for(
                    "main.Project_edit",
                    project_id=project_id
                )
            )

        if status not in VALID_PROJECT_STATUSES:
            flash("Please select a valid project status.", "danger")

            return redirect(
                url_for(
                    "main.Project_edit",
                    project_id=project_id
                )
            )

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()

        except (TypeError, ValueError):
            flash("Please provide valid project dates.", "danger")

            return redirect(
                url_for(
                    "main.Project_edit",
                    project_id=project_id
                )
            )

        if end < start:
            flash(
                "End date cannot be earlier than the start date.",
                "danger"
            )

            return redirect(
                url_for(
                    "main.Project_edit",
                    project_id=project_id
                )
            )

        selected_program = None

        if program_id:
            try:
                selected_program = Program_model.query.filter_by(
                    program_id=int(program_id),
                    user_id=current_user.id
                ).first()

            except ValueError:
                selected_program = None

            if selected_program is None:
                flash("Please select a valid parent program.", "danger")

                return redirect(
                    url_for(
                        "main.Project_edit",
                        project_id=project_id
                    )
                )

        project.project_name = project_name
        project.program_id = (
            selected_program.program_id
            if selected_program
            else None
        )
        project.description = description
        project.involvement = involvement
        project.start_date = start
        project.end_date = end
        project.status = status

        db.session.commit()

        flash("Extension project updated successfully.", "success")
        return redirect(url_for("main.Project"))

    return render_template(
        "Project_edit.html",
        project=project,
        programs=programs
    )


@main.route("/projects/delete/<int:project_id>", methods=["POST"])
@login_required
def delete_project(project_id):
    if current_user.role != "FACULTY":
        flash(
            "Only the Faculty Extensionist can manage extension projects.",
            "danger"
        )
        return redirect(url_for("main.Project"))

    project = Project_model.query.get_or_404(project_id)

    if project.user_id != current_user.id:
        flash(
            "You can only manage extension projects you created.",
            "danger"
        )
        return redirect(url_for("main.Project"))

    db.session.delete(project)
    db.session.commit()

    flash("Extension project deleted successfully.", "success")
    return redirect(url_for("main.Project"))

def _faculty_activity_query():
    return (
        Activity_model.query
        .filter_by(user_id=current_user.id)
        .order_by(
            Activity_model.updated_at.desc(),
            Activity_model.start_date.desc()
        )
    )


def _parse_activity_parent(parent_value):
    if not parent_value or ":" not in parent_value:
        return None, None

    kind, raw_id = parent_value.split(":", 1)

    try:
        item_id = int(raw_id)

    except ValueError:
        return None, None

    if kind == "program":
        return item_id, None

    if kind == "project":
        return None, item_id

    return None, None


@main.route("/activities")
@login_required
def Activity():
    if current_user.role not in ("FACULTY", "COORDINATOR"):
        flash(
            "You are not authorized to view extension activities.",
            "danger"
        )
        return redirect(url_for("main.index"))

    can_manage = current_user.role == "FACULTY"

    if can_manage:
        query = _faculty_activity_query()
        base_template = "base_faculty.html"

    else:
        query = Activity_model.query.order_by(
            Activity_model.updated_at.desc(),
            Activity_model.start_date.desc()
        )
        base_template = "base_coordinator.html"

    search = request.args.get("search", "").strip()
    parent = request.args.get("parent", "all")
    status = request.args.get("status", "all")
    date_range = request.args.get("date_range", "all")

    if search:
        query = query.filter(
            Activity_model.activity_name.ilike(f"%{search}%")
        )

    if status != "all" and status in VALID_ACTIVITY_STATUSES:
        query = query.filter(Activity_model.status == status)

    if parent.startswith("program:"):
        try:
            program_id = int(parent.split(":", 1)[1])
            query = query.filter(Activity_model.program_id == program_id)

        except ValueError:
            pass

    elif parent.startswith("project:"):
        try:
            project_id = int(parent.split(":", 1)[1])
            query = query.filter(Activity_model.project_id == project_id)

        except ValueError:
            pass

    today = datetime.utcnow().date()

    if date_range == "month":
        query = query.filter(
            Activity_model.start_date <= today,
            Activity_model.end_date >= today
        )

    elif date_range == "upcoming":
        query = query.filter(Activity_model.start_date >= today)

    elif date_range == "past":
        query = query.filter(Activity_model.end_date < today)

    activities = query.all()

    if can_manage:
        all_activities = (
            Activity_model.query
            .filter_by(user_id=current_user.id)
            .all()
        )

    else:
        all_activities = Activity_model.query.all()

    stats = {
        "total": len(all_activities),
        "completed": sum(
            activity.status == "Completed"
            for activity in all_activities
        ),
        "ongoing": sum(
            activity.status == "Ongoing"
            for activity in all_activities
        ),
        "pending": sum(
            activity.status == "Pending"
            for activity in all_activities
        ),
        "cancelled": sum(
            activity.status == "Cancelled"
            for activity in all_activities
        ),
    }

    if can_manage:
        programs = (
            Program_model.query
            .filter_by(user_id=current_user.id)
            .order_by(Program_model.program_name.asc())
            .all()
        )

        projects = (
            Project_model.query
            .filter_by(user_id=current_user.id)
            .order_by(Project_model.project_name.asc())
            .all()
        )

    else:
        programs = (
            Program_model.query
            .order_by(Program_model.program_name.asc())
            .all()
        )

        projects = (
            Project_model.query
            .order_by(Project_model.project_name.asc())
            .all()
        )

    return render_template(
        "Activities.html",
        activities=activities,
        programs=programs,
        projects=projects,
        stats=stats,
        search=search,
        parent=parent,
        status=status,
        date_range=date_range,
        base_template=base_template,
        can_manage=can_manage
    )


@main.route("/activities/add", methods=["GET", "POST"])
@login_required
def Activity_add():
    if current_user.role != "FACULTY":
        flash(
            "Only the Faculty Extensionist can manage extension activities.",
            "danger"
        )
        return redirect(url_for("main.index"))

    programs = (
        Program_model.query
        .filter_by(user_id=current_user.id)
        .order_by(Program_model.program_name.asc())
        .all()
    )

    projects = (
        Project_model.query
        .filter_by(user_id=current_user.id)
        .order_by(Project_model.project_name.asc())
        .all()
    )

    if request.method == "POST":
        activity_name = request.form.get("activity_name", "").strip()
        activity_type = request.form.get("activity_type", "").strip()
        parent_value = request.form.get("parent", "")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        status = request.form.get("status")
        description = request.form.get("description", "").strip()

        try:
            participants_attended = max(
                0,
                int(request.form.get("participants_attended") or 0)
            )

            participants_target = max(
                0,
                int(request.form.get("participants_target") or 0)
            )

        except ValueError:
            flash("Participant counts must be whole numbers.", "danger")
            return redirect(url_for("main.Activity_add"))

        if participants_target and participants_attended > participants_target:
            flash(
                "Participants reached cannot exceed the target.",
                "danger"
            )
            return redirect(url_for("main.Activity_add"))

        program_id, project_id = _parse_activity_parent(parent_value)

        if not program_id and not project_id:
            flash("Please select a program or project.", "danger")
            return redirect(url_for("main.Activity_add"))

        if program_id:
            parent_ok = Program_model.query.filter_by(
                program_id=program_id,
                user_id=current_user.id
            ).first()

        else:
            parent_ok = Project_model.query.filter_by(
                project_id=project_id,
                user_id=current_user.id
            ).first()

        if parent_ok is None:
            flash("Please select a valid program or project.", "danger")
            return redirect(url_for("main.Activity_add"))

        if status not in VALID_ACTIVITY_STATUSES:
            flash("Please select a valid activity status.", "danger")
            return redirect(url_for("main.Activity_add"))

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()

        except (TypeError, ValueError):
            flash("Please provide valid activity dates.", "danger")
            return redirect(url_for("main.Activity_add"))

        if end < start:
            flash(
                "End date cannot be earlier than the start date.",
                "danger"
            )
            return redirect(url_for("main.Activity_add"))

        activity = Activity_model(
            user_id=current_user.id,
            program_id=program_id,
            project_id=project_id,
            activity_name=activity_name,
            activity_type=activity_type or "Extension Activity",
            start_date=start,
            end_date=end,
            status=status,
            participants_attended=participants_attended,
            participants_target=participants_target,
            description=description
        )

        db.session.add(activity)
        db.session.commit()

        flash("Extension activity added successfully.", "success")
        return redirect(url_for("main.Activity"))

    return render_template(
        "Activity_add.html",
        programs=programs,
        projects=projects
    )


@main.route("/activities/edit/<int:activity_id>", methods=["GET", "POST"])
@login_required
def Activity_edit(activity_id):
    if current_user.role != "FACULTY":
        flash(
            "Only the Faculty Extensionist can manage extension activities.",
            "danger"
        )
        return redirect(url_for("main.index"))

    activity = Activity_model.query.get_or_404(activity_id)

    if activity.user_id != current_user.id:
        flash(
            "You can only manage extension activities you created.",
            "danger"
        )
        return redirect(url_for("main.Activity"))

    programs = (
        Program_model.query
        .filter_by(user_id=current_user.id)
        .order_by(Program_model.program_name.asc())
        .all()
    )

    projects = (
        Project_model.query
        .filter_by(user_id=current_user.id)
        .order_by(Project_model.project_name.asc())
        .all()
    )

    if request.method == "POST":
        parent_value = request.form.get("parent", "")
        program_id, project_id = _parse_activity_parent(parent_value)

        if not program_id and not project_id:
            flash("Please select a program or project.", "danger")

            return redirect(
                url_for(
                    "main.Activity_edit",
                    activity_id=activity_id
                )
            )

        if program_id:
            parent_ok = Program_model.query.filter_by(
                program_id=program_id,
                user_id=current_user.id
            ).first()

        else:
            parent_ok = Project_model.query.filter_by(
                project_id=project_id,
                user_id=current_user.id
            ).first()

        if parent_ok is None:
            flash("Please select a valid program or project.", "danger")

            return redirect(
                url_for(
                    "main.Activity_edit",
                    activity_id=activity_id
                )
            )

        status = request.form.get("status")

        if status not in VALID_ACTIVITY_STATUSES:
            flash("Please select a valid activity status.", "danger")

            return redirect(
                url_for(
                    "main.Activity_edit",
                    activity_id=activity_id
                )
            )

        try:
            start = datetime.strptime(
                request.form.get("start_date"),
                "%Y-%m-%d"
            ).date()

            end = datetime.strptime(
                request.form.get("end_date"),
                "%Y-%m-%d"
            ).date()

            attended = max(
                0,
                int(request.form.get("participants_attended") or 0)
            )

            target = max(
                0,
                int(request.form.get("participants_target") or 0)
            )

        except (TypeError, ValueError):
            flash(
                "Please provide valid dates and participant counts.",
                "danger"
            )

            return redirect(
                url_for(
                    "main.Activity_edit",
                    activity_id=activity_id
                )
            )

        if end < start:
            flash(
                "End date cannot be earlier than the start date.",
                "danger"
            )

            return redirect(
                url_for(
                    "main.Activity_edit",
                    activity_id=activity_id
                )
            )

        if target and attended > target:
            flash(
                "Participants reached cannot exceed the target.",
                "danger"
            )

            return redirect(
                url_for(
                    "main.Activity_edit",
                    activity_id=activity_id
                )
            )

        activity.program_id = program_id
        activity.project_id = project_id
        activity.activity_name = request.form.get("activity_name", "").strip()
        activity.activity_type = (
            request.form.get("activity_type", "").strip()
            or "Extension Activity"
        )
        activity.start_date = start
        activity.end_date = end
        activity.status = status
        activity.participants_attended = attended
        activity.participants_target = target
        activity.description = request.form.get("description", "").strip()

        db.session.commit()

        flash("Extension activity updated successfully.", "success")
        return redirect(url_for("main.Activity"))

    if activity.program_id:
        parent_value = f"program:{activity.program_id}"

    elif activity.project_id:
        parent_value = f"project:{activity.project_id}"

    else:
        parent_value = ""

    return render_template(
        "Activity_edit.html",
        activity=activity,
        programs=programs,
        projects=projects,
        parent_value=parent_value
    )

@main.route("/activities/delete/<int:activity_id>", methods=["POST"])
@login_required
def delete_activity(activity_id):
    if current_user.role != "FACULTY":
        flash(
            "Only the Faculty Extensionist can manage extension activities.",
            "danger"
        )
        return redirect(url_for("main.index"))

    activity = Activity_model.query.get_or_404(activity_id)

    if activity.user_id != current_user.id:
        flash(
            "You can only manage extension activities you created.",
            "danger"
        )
        return redirect(url_for("main.Activity"))

    db.session.delete(activity)
    db.session.commit()

    flash("Extension activity deleted successfully.", "success")
    return redirect(url_for("main.Activity"))

# ============================================================
# BUDGET UTILIZATION
# ============================================================

def _budget_fiscal_year():
    return datetime.utcnow().year


def _budget_totals(fiscal_year, faculty_only=False):
    query = BudgetItem_model.query.filter_by(fiscal_year=fiscal_year)

    if faculty_only:
        query = query.filter_by(user_id=current_user.id)

    items = query.order_by(BudgetItem_model.created_at.desc()).all()

    allocated = sum(float(item.allocated_amount or 0) for item in items)
    utilized = sum(float(item.utilized_amount or 0) for item in items)

    return items, allocated, utilized


def _budget_parent_options():
    if current_user.role == "FACULTY":
        programs = Program_model.query.filter_by(
            user_id=current_user.id
        ).order_by(Program_model.program_name.asc()).all()

        projects = Project_model.query.filter_by(
            user_id=current_user.id
        ).order_by(Project_model.project_name.asc()).all()

        activities = Activity_model.query.filter_by(
            user_id=current_user.id
        ).order_by(Activity_model.activity_name.asc()).all()

    else:
        programs = Program_model.query.order_by(
            Program_model.program_name.asc()
        ).all()

        projects = Project_model.query.order_by(
            Project_model.project_name.asc()
        ).all()

        activities = Activity_model.query.order_by(
            Activity_model.activity_name.asc()
        ).all()

    return programs, projects, activities


@main.route("/budget-utilization")
@login_required
def BudgetUtilization():
    if current_user.role not in ("FACULTY", "COORDINATOR", "DEAN"):
        flash("You are not authorized to view budget utilization.", "danger")
        return redirect(url_for("main.index"))

    fiscal_year = request.args.get("year", type=int) or _budget_fiscal_year()

    allocation = BudgetAllocation_model.query.filter_by(
        fiscal_year=fiscal_year
    ).first()

    allocations = BudgetAllocation_model.query.order_by(
        BudgetAllocation_model.fiscal_year.desc()
    ).all()

    faculty_only = current_user.role == "FACULTY"
    items, item_allocated, utilized = _budget_totals(
        fiscal_year,
        faculty_only=faculty_only
    )

    # Coordinator and Dean: overall annual allocation.
    # Faculty: total of that faculty member's submitted breakdown.
    if current_user.role == "FACULTY":
        overall = item_allocated
    else:
        overall = float(allocation.amount or 0) if allocation else 0.0

    remaining = max(0.0, overall - utilized)
    utilization_rate = (utilized / overall * 100) if overall > 0 else 0.0
    utilization_rate = min(utilization_rate, 100.0)

    programs, projects, activities = _budget_parent_options()

    if current_user.role == "COORDINATOR":
        base_template = "base_coordinator.html"
    elif current_user.role == "DEAN":
        base_template = "base_dean.html"
    else:
        base_template = "base_faculty.html"

    return render_template(
        "BudgetUtilization.html",
        allocation=allocation,
        allocations=allocations,
        items=items,
        item_allocated=item_allocated,
        utilized=utilized,
        overall=overall,
        remaining=remaining,
        utilization_rate=utilization_rate,
        fiscal_year=fiscal_year,
        programs=programs,
        projects=projects,
        activities=activities,
        base_template=base_template,
        can_allocate=current_user.role == "COORDINATOR",
        can_submit=current_user.role == "FACULTY",
        is_dean=current_user.role == "DEAN"
    )


@main.route("/budget-utilization/allocate", methods=["POST"])
@login_required
def BudgetUtilization_allocate():
    if current_user.role != "COORDINATOR":
        flash("Only the Extension Coordinator can allocate the overall budget.", "danger")
        return redirect(url_for("main.BudgetUtilization"))

    try:
        fiscal_year = int(
            request.form.get("fiscal_year", _budget_fiscal_year())
        )
        amount = float(request.form.get("amount", 0))
    except (TypeError, ValueError):
        flash("Please enter a valid fiscal year and budget amount.", "danger")
        return redirect(url_for("main.BudgetUtilization"))

    if fiscal_year < 2000:
        flash("Please enter a valid fiscal year.", "danger")
        return redirect(url_for("main.BudgetUtilization"))

    if amount < 0:
        flash("Budget amount cannot be negative.", "danger")
        return redirect(url_for("main.BudgetUtilization"))

    allocation = BudgetAllocation_model.query.filter_by(
        fiscal_year=fiscal_year
    ).first()

    if allocation:
        allocation.amount = amount
        allocation.allocated_by = current_user.id
        allocation.status = "Active"
        allocation.updated_at = datetime.utcnow()
    else:
        allocation = BudgetAllocation_model(
            fiscal_year=fiscal_year,
            amount=amount,
            allocated_by=current_user.id,
            date_allocated=datetime.utcnow(),
            status="Active",
            updated_at=datetime.utcnow()
        )
        db.session.add(allocation)

    for old in BudgetAllocation_model.query.filter(
        BudgetAllocation_model.fiscal_year < fiscal_year,
        BudgetAllocation_model.status == "Active"
    ).all():
        old.status = "Completed"

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print("Budget allocation error:", exc)
        flash("An error occurred while saving the budget allocation.", "danger")
        return redirect(url_for("main.BudgetUtilization", year=fiscal_year))

    flash(
        f"Overall budget for Fiscal Year {fiscal_year} was saved successfully.",
        "success"
    )
    return redirect(url_for("main.BudgetUtilization", year=fiscal_year))


@main.route("/budget-utilization/items/add", methods=["POST"])
@login_required
def BudgetUtilization_item_add():
    if current_user.role != "FACULTY":
        flash("Only Faculty Extensionists can submit budget breakdowns.", "danger")
        return redirect(url_for("main.BudgetUtilization"))

    fiscal_year = (
        request.form.get("fiscal_year", type=int)
        or _budget_fiscal_year()
    )

    # IMPORTANT: every BudgetItem must belong to the active annual allocation.
    allocation = BudgetAllocation_model.query.filter_by(
        fiscal_year=fiscal_year,
        status="Active"
    ).first()

    if allocation is None:
        flash(
            f"No active budget allocation exists for Fiscal Year {fiscal_year}. "
            "Please wait for the Extension Coordinator to allocate the budget.",
            "warning"
        )
        return redirect(url_for("main.BudgetUtilization", year=fiscal_year))

    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    parent = request.form.get("parent", "").strip()

    try:
        allocated_amount = float(
            request.form.get("allocated_amount", 0)
        )
        utilized_amount = float(
            request.form.get("utilized_amount", 0)
        )
    except (TypeError, ValueError):
        flash("Please enter valid budget amounts.", "danger")
        return redirect(url_for("main.BudgetUtilization", year=fiscal_year))

    if not category or not description:
        flash("Please complete the budget category and description.", "danger")
        return redirect(url_for("main.BudgetUtilization", year=fiscal_year))

    if allocated_amount <= 0:
        flash("Allocated amount must be greater than zero.", "danger")
        return redirect(url_for("main.BudgetUtilization", year=fiscal_year))

    if utilized_amount < 0 or utilized_amount > allocated_amount:
        flash(
            "Utilized amount must be between zero and the allocated amount.",
            "danger"
        )
        return redirect(url_for("main.BudgetUtilization", year=fiscal_year))

    program_id = None
    project_id = None
    activity_id = None

    if ":" in parent:
        kind, raw_id = parent.split(":", 1)
        try:
            parent_id = int(raw_id)
        except (TypeError, ValueError):
            parent_id = None

        if parent_id:
            if kind == "program":
                obj = Program_model.query.filter_by(
                    program_id=parent_id,
                    user_id=current_user.id
                ).first()
                if obj:
                    program_id = obj.program_id

            elif kind == "project":
                obj = Project_model.query.filter_by(
                    project_id=parent_id,
                    user_id=current_user.id
                ).first()
                if obj:
                    project_id = obj.project_id

            elif kind == "activity":
                obj = Activity_model.query.filter_by(
                    activity_id=parent_id,
                    user_id=current_user.id
                ).first()
                if obj:
                    activity_id = obj.activity_id

    if not any((program_id, project_id, activity_id)):
        flash("Please select a valid program, project, or activity.", "danger")
        return redirect(url_for("main.BudgetUtilization", year=fiscal_year))

    # Check the shared annual utilization before accepting the new entry.
    _, _, current_utilized = _budget_totals(
        fiscal_year,
        faculty_only=False
    )

    overall_budget = float(allocation.amount or 0)

    if current_utilized + utilized_amount > overall_budget:
        flash(
            "The submitted utilized amount would exceed the overall allocated budget.",
            "danger"
        )
        return redirect(url_for("main.BudgetUtilization", year=fiscal_year))

    # IMPORTANT FIX:
    # budget_id is required by the database, so explicitly link the item
    # to the coordinator's annual BudgetAllocation record.
    item = BudgetItem_model(
        budget_id=allocation.budget_id,
        user_id=current_user.id,
        fiscal_year=fiscal_year,
        program_id=program_id,
        project_id=project_id,
        activity_id=activity_id,
        category=category,
        description=description,
        allocated_amount=allocated_amount,
        utilized_amount=utilized_amount,
        supporting_document=None
    )

    try:
        db.session.add(item)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print("Budget item error:", exc)
        flash("An error occurred while saving the budget entry.", "danger")
        return redirect(url_for("main.BudgetUtilization", year=fiscal_year))

    flash("Budget breakdown submitted successfully.", "success")
    return redirect(url_for("main.BudgetUtilization", year=fiscal_year))


@main.route("/budget-utilization/items/delete/<int:item_id>", methods=["POST"])
@login_required
def BudgetUtilization_item_delete(item_id):
    if current_user.role != "FACULTY":
        flash("Only Faculty Extensionists can delete their budget entries.", "danger")
        return redirect(url_for("main.BudgetUtilization"))

    item = BudgetItem_model.query.get_or_404(item_id)

    if item.user_id != current_user.id:
        flash("You can only delete your own budget entries.", "danger")
        return redirect(url_for("main.BudgetUtilization"))

    try:
        db.session.delete(item)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        print("Budget delete error:", exc)
        flash("An error occurred while deleting the budget entry.", "danger")
        return redirect(url_for("main.BudgetUtilization"))

    flash("Budget entry deleted successfully.", "success")
    return redirect(url_for("main.BudgetUtilization"))

