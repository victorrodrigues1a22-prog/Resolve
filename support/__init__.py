"""Configuração da aplicação Flask."""
import os
from pathlib import Path
from flask import Flask, g, session
from .db import init_db, get_db

BASE_DIR = Path(__file__).resolve().parent.parent

def create_app():
    app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"), instance_path=str(BASE_DIR / "instance"), instance_relative_config=True)
    app.config.update(SECRET_KEY=os.environ.get("SECRET_KEY", "troque-esta-chave-antes-de-publicar"), DATABASE=os.environ.get("TICKETS_DATABASE", str(BASE_DIR / "chamados.db")))
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    init_db(app)

    from .routes.auth import bp as auth_bp
    from .routes.dashboard import bp as dashboard_bp
    from .routes.tickets import bp as tickets_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(tickets_bp)

    @app.teardown_appcontext
    def close_db(_error=None):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.context_processor
    def shared_context():
        user = None
        if session.get("user_id"):
            user = get_db().execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        return {"me": user, "statuses": {"aberto":"Aberto", "em_atendimento":"Em atendimento", "aguardando_usuario":"Aguardando você", "resolvido":"Resolvido"}, "priorities": {"baixa":"Baixa", "media":"Média", "alta":"Alta", "critica":"Crítica"}}

    @app.template_filter("datetime_display")
    def datetime_display(value):
        from datetime import datetime
        try: return datetime.fromisoformat(value).astimezone().strftime("%d/%m/%Y às %H:%M")
        except (ValueError, TypeError): return value

    @app.errorhandler(403)
    def forbidden(_error):
        from flask import render_template
        return render_template("error.html", code=403, message="Este perfil não tem acesso a esta página."), 403

    return app
