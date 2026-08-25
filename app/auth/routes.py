from urllib.parse import urljoin, urlparse

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_user,
    logout_user,
)

from . import auth_bp
from ..models import User


def is_safe_next_url(target):
    if not target:
        return False

    host_url = urlparse(request.host_url)
    target_url = urlparse(
        urljoin(
            request.host_url,
            target,
        )
    )

    return (
        target_url.scheme
        in {"http", "https"}
        and host_url.netloc
        == target_url.netloc
    )


@auth_bp.route(
    "/login",
    methods=["GET", "POST"],
)
def login():
    if current_user.is_authenticated:
        return redirect(
            url_for("main.index")
        )

    if request.method == "POST":
        username = (
            request.form.get(
                "username",
                "",
            )
            .strip()
        )

        password = request.form.get(
            "password",
            "",
        )

        user = (
            User.query
            .filter_by(username=username)
            .first()
        )

        if (
            user is None
            or not user.is_enabled
            or not user.check_password(password)
        ):
            flash(
                "Hibás felhasználónév vagy jelszó.",
                "error",
            )

            return render_template(
                "auth/login.html",
            )

        login_user(user)

        next_url = request.args.get("next")

        if is_safe_next_url(next_url):
            return redirect(next_url)

        return redirect(
            url_for("main.index")
        )

    return render_template(
        "auth/login.html",
    )


@auth_bp.route(
    "/logout",
    methods=["POST"],
)
def logout():
    if current_user.is_authenticated:
        logout_user()

    return redirect(
        url_for("auth.login")
    )
