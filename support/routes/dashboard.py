from flask import Blueprint, redirect, render_template, request, session, url_for
from ..auth import current_user, login_required
from ..db import get_db
bp = Blueprint("dashboard", __name__)

@bp.route("/")
def root(): return redirect(url_for("dashboard.index") if session.get("user_id") else url_for("auth.login"))

@bp.route("/chamados")
@login_required
def index():
    conn=get_db(); user=current_user()
    if user["role"] == "ti":
        filters=[]; params=[]
        if request.args.get("status"):
            filters.append("t.status=?"); params.append(request.args["status"])
        if request.args.get("category"):
            filters.append("t.category=?"); params.append(request.args["category"])
        where=("WHERE "+" AND ".join(filters)) if filters else ""
        tickets=conn.execute(f"SELECT t.*,u.name author,assignee.name assigned_name FROM tickets t JOIN users u ON u.id=t.user_id LEFT JOIN users assignee ON assignee.id=t.assigned_to {where} ORDER BY CASE t.status WHEN 'aberto' THEN 0 WHEN 'aguardando_usuario' THEN 1 WHEN 'em_atendimento' THEN 2 ELSE 3 END, (t.affected_count*CASE t.business_impact WHEN 'critico' THEN 4 WHEN 'alto' THEN 3 WHEN 'medio' THEN 2 ELSE 1 END*CASE t.priority WHEN 'critica' THEN 4 WHEN 'alta' THEN 3 WHEN 'media' THEN 2 ELSE 1 END) DESC,t.created_at",params).fetchall()
        stats=conn.execute("SELECT COUNT(*) total,SUM(status IN ('aberto','em_atendimento','aguardando_usuario')) active,AVG(CASE WHEN first_response_at IS NOT NULL THEN (julianday(first_response_at)-julianday(created_at))*1440 END) response_minutes,AVG(CASE WHEN resolved_at IS NOT NULL THEN (julianday(resolved_at)-julianday(created_at))*1440 END) resolution_minutes,AVG(satisfaction) satisfaction FROM tickets").fetchone()
        techs=conn.execute("SELECT id,name FROM users WHERE role='ti'").fetchall()
        return render_template("ti_dashboard.html",tickets=tickets,stats=stats,techs=techs)
    tickets=conn.execute("SELECT * FROM tickets WHERE user_id=? ORDER BY created_at DESC",(user["id"],)).fetchall()
    active=conn.execute("SELECT id FROM tickets WHERE user_id=? AND status!='resolvido' LIMIT 1",(user["id"],)).fetchone()
    notices=conn.execute("SELECT e.*,t.title FROM ticket_events e JOIN tickets t ON t.id=e.ticket_id WHERE t.user_id=? AND e.user_id IS NOT NULL AND e.user_id!=? ORDER BY e.created_at DESC LIMIT 8",(user["id"],user["id"])).fetchall()
    return render_template("user_dashboard.html",tickets=tickets,has_active=bool(active),notices=notices)
