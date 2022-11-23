"""Routes for user authentication."""
from crypt import methods
from flask import redirect, render_template, flash, request, session, url_for
from flask_login import login_required, logout_user, current_user, login_user

from vnncomp.main import app
from vnncomp import login_manager, db
from vnncomp.utils.aws_instance import AwsInstance
from vnncomp.utils.forms import SignupForm, LoginForm
from vnncomp.utils.user import User


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Log-in page for registered users.

    GET requests serve Log-in page.
    POST requests validate and redirect user to dashboard.
    """
    # Bypass if user is logged in
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()
    # Validate login attempt
    if form.validate_on_submit():
        user: User = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(password=form.password.data):
            if user.enabled:
                login_user(user)
                next_page = request.args.get("next")
                return redirect(next_page or url_for("index"))
            else:
                flash(
                    "Your account has not been activated. This needs to be done by the organizers."
                )
                return redirect(url_for("login"))
        flash("Invalid username/password combination")
        return redirect(url_for("login"))
    return render_template(
        "user/login.html",
        form=form,
        title="Log in.",
        template="login-page",
        body="Log in with your User account.",
    )


@app.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """
    User sign-up page.

    GET requests serve sign-up page.
    POST requests validate form & user creation.
    """
    form = SignupForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user is None:
            user = User(username=form.username.data, enabled=False)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()  # Create new user
            flash(
                "Your account was created, but needs to be activated by the organizers."
            )
            return redirect(url_for("login"))
        flash("A user already exists with that email address.")
    return render_template(
        "user/signup.html",
        title="Create an Account.",
        form=form,
        template="signup-page",
        body="Sign up for a user account.",
    )


@app.route("/admin", methods=["GET"])
@login_required
def admin():
    """
    Admin page
    """
    if not current_user.admin:
        return "You need to be an admin to access this page."

    # c = AwsInstance.query.

    return render_template("user/admin.html", users=User.query.all())


@app.route("/enable_user/<id>", methods=["GET"])
@login_required
def enable_user(id):
    if not current_user.admin:
        return "You need to be an admin to access this page."

    user: User = User.query.get(id)
    user.enable()

    return redirect("/admin")


@app.route("/disable_user/<id>", methods=["GET"])
@login_required
def disable_user(id):
    if not current_user.admin:
        return "You need to be an admin to access this page."

    user: User = User.query.get(id)
    user.disable()

    return redirect("/admin")


@login_manager.user_loader
def load_user(user_id):
    """Check if user is logged-in on every page load."""
    if user_id is not None:
        user: User = User.query.get(user_id)
        if user.enabled:
            return user
    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to Login page."""
    flash("You must be logged in to view that page.")
    return redirect(url_for("login"))
