"""Cria uma conta da equipe de TI: python -m support.create_ti"""
from getpass import getpass
import re
from werkzeug.security import generate_password_hash
from . import create_app
from .db import get_db

def main():
    app=create_app()
    with app.app_context():
        name=input("Nome da pessoa técnica: ").strip()
        username=input("Nome de usuário: ").strip().lower()
        email=input("E-mail: ").strip().lower()
        password=getpass("Senha (mínimo 12 caracteres): ")
        confirm=getpass("Confirme a senha: ")
        if len(name)<2 or not re.fullmatch(r"[a-z0-9_.-]{3,32}",username) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",email):
            raise SystemExit("Nome, usuário ou e-mail inválido.")
        if len(password)<12 or password!=confirm:
            raise SystemExit("Senha muito curta ou confirmação diferente.")
        conn=get_db()
        duplicate=conn.execute("SELECT 1 FROM users WHERE username=? COLLATE NOCASE OR email=? COLLATE NOCASE",(username,email)).fetchone()
        if duplicate: raise SystemExit("Já existe uma conta com esse usuário ou e-mail.")
        conn.execute("INSERT INTO users(name,role,username,email,password_hash,is_active) VALUES(?,'ti',?,?,?,1)",(name,username,email,generate_password_hash(password)))
        conn.commit()
        print("Conta da equipe de TI criada.")

if __name__=="__main__": main()
