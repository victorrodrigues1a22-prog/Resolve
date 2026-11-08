"""Cadastro de solicitantes e autenticação por senha."""
import re
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from ..db import get_db

bp = Blueprint("auth", __name__)

@bp.route("/entrar", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE is_active=1 AND (username=? COLLATE NOCASE OR email=? COLLATE NOCASE)", (identity, identity)).fetchone()
        if user and user["password_hash"] and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard.index"))
        flash("Usuário/e-mail ou senha inválidos.", "erro")
    return render_template("login.html", mode="login")

@bp.route("/cadastro", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        name=request.form.get("name", "").strip()
        username=request.form.get("username", "").strip().lower()
        email=request.form.get("email", "").strip().lower()
        password=request.form.get("password", "")
        confirm=request.form.get("confirm_password", "")
        errors=[]
        if not 2 <= len(name) <= 100: errors.append("Informe seu nome (2 a 100 caracteres).")
        if not re.fullmatch(r"[a-z0-9_.-]{3,32}", username): errors.append("O usuário deve ter 3–32 caracteres: letras, números, ponto, hífen ou sublinhado.")
        if len(email)>254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email): errors.append("Informe um e-mail válido.")
        if len(password)<12: errors.append("A senha precisa ter pelo menos 12 caracteres.")
        if password!=confirm: errors.append("A confirmação da senha não confere.")
        conn=get_db()
        if username and conn.execute("SELECT 1 FROM users WHERE username=? COLLATE NOCASE",(username,)).fetchone(): errors.append("Esse nome de usuário já está em uso.")
        if email and conn.execute("SELECT 1 FROM users WHERE email=? COLLATE NOCASE",(email,)).fetchone(): errors.append("Já existe uma conta com esse e-mail.")
        if errors:
            for error in errors: flash(error,"erro")
        else:
            conn.execute("INSERT INTO users(name,role,username,email,password_hash,is_active) VALUES(?,?,?,?,?,1)",(name,"usuario",username,email,generate_password_hash(password)))
            conn.commit()
            user=conn.execute("SELECT id FROM users WHERE username=? COLLATE NOCASE",(username,)).fetchone()
            session.clear(); session["user_id"]=user["id"]
            flash("Conta criada. Você já pode registrar um chamado.","sucesso")
            return redirect(url_for("dashboard.index"))
    return render_template("login.html", mode="register")

@bp.post("/sair")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
