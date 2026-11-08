"""Autorização central por perfil."""
from functools import wraps
from flask import abort, redirect, session, url_for
from .db import get_db

def current_user():
    uid = session.get("user_id")
    return get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone() if uid else None

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user(): return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)
    return wrapped

def ti_required(fn):
    @wraps(fn)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user()["role"] != "ti": abort(403)
        return fn(*args, **kwargs)
    return wrapped

def requester_or_ti(ticket_id):
    ticket = get_db().execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    if not ticket: abort(404)
    user = current_user()
    if user["role"] != "ti" and ticket["user_id"] != user["id"]: abort(403)
    return ticket
