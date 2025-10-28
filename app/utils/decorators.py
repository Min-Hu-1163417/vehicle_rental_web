from functools import wraps

from flask import session, redirect, url_for, flash


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "uid" not in session:
            flash("Please login first")
            return redirect(url_for("auth.login_form"))
        return fn(*args, **kwargs)

    return wrapper


def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            role = session.get("role")
            if role not in roles:
                flash("Insufficient permission")
                return redirect(url_for("views.home"))
            return fn(*args, **kwargs)

        return wrapper

    return deco
