"""Telas e ações dos chamados: triagem, conversa e acompanhamento."""
from datetime import datetime
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from ..auth import current_user, login_required, requester_or_ti, ti_required
from ..db import get_db
bp=Blueprint("tickets",__name__)
PRIORITIES={"baixa","media","alta","critica"}; STATUSES={"aberto","em_atendimento","aguardando_usuario","resolvido"}
CATEGORIES={"acesso":"Acesso e contas","equipamento":"Equipamentos","sistema":"Sistemas e aplicativos","rede":"Rede e conectividade","impressora":"Impressão","outros":"Outro"}
def now(): return datetime.now().astimezone().isoformat(timespec="seconds")
def event(conn,ticket_id,user_id,kind,details=""):
    conn.execute("INSERT INTO ticket_events(ticket_id,user_id,event_type,details,created_at) VALUES(?,?,?,?,?)",(ticket_id,user_id,kind,details,now()))

@bp.get("/ajuda")
@login_required
def knowledge():
    query=request.args.get("q","").strip().casefold()
    articles=get_db().execute("SELECT * FROM knowledge_articles ORDER BY category,title").fetchall()
    if query: articles=[a for a in articles if query in (a["title"]+" "+a["keywords"]+" "+a["body"]).casefold()]
    return render_template("knowledge.html",articles=articles,query=request.args.get("q",""))

@bp.route("/chamados/novo",methods=["GET","POST"])
@login_required
def new():
    user=current_user()
    if user["role"]!="usuario": abort(403)
    conn=get_db()
    if conn.execute("SELECT id FROM tickets WHERE user_id=? AND status!='resolvido' LIMIT 1",(user["id"],)).fetchone():
        flash("Você já tem um chamado em andamento. Aguarde a conclusão.","erro"); return redirect(url_for("dashboard.index"))
    if request.method=="POST":
        title=request.form.get("title","").strip(); description=request.form.get("description","").strip(); category=request.form.get("category",""); system=request.form.get("system_name","").strip(); impact=request.form.get("business_impact",""); count=request.form.get("affected_count","1"); priority=request.form.get("priority","")
        try: count=max(1,min(10000,int(count)))
        except ValueError: count=1
        if not 4<=len(title)<=100 or not 15<=len(description)<=3000 or category not in CATEGORIES or priority not in PRIORITIES or impact not in {"baixo","medio","alto","critico"}:
            flash("Confira o resumo, a descrição e os campos da triagem.","erro")
        else:
            stamp=now(); incident_key=f"{category}:{system.casefold()}" if system else ""
            conn.execute("INSERT INTO tickets(user_id,title,description,priority,status,created_at,updated_at,category,system_name,affected_count,business_impact,incident_key) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(user["id"],title,description,priority,"aberto",stamp,stamp,category,system,count,impact,incident_key)); tid=conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            event(conn,tid,user["id"],"aberto","Chamado registrado")
            similar=[]
            if incident_key:
                similar=conn.execute("SELECT id,title FROM tickets WHERE incident_key=? AND id!=? AND status!='resolvido' ORDER BY created_at DESC LIMIT 5",(incident_key,tid)).fetchall()
                if similar:
                    conn.execute("UPDATE tickets SET incident_key=? WHERE id=?",(incident_key,tid))
                    event(conn,tid,user["id"],"incidente",f"Possível incidente relacionado a {len(similar)} chamado(s)")
            conn.commit()
            if similar: flash(f"Chamado enviado. Encontramos {len(similar)} chamado(s) ativo(s) do mesmo sistema; a TI verá a possível ocorrência conjunta.","sucesso")
            else: flash("Chamado enviado para a equipe de TI.","sucesso")
            return redirect(url_for("dashboard.index"))
    articles=get_db().execute("SELECT * FROM knowledge_articles ORDER BY title").fetchall()
    return render_template("new_ticket.html",categories=CATEGORIES,articles=articles)

@bp.route("/chamados/<int:ticket_id>")
@login_required
def detail(ticket_id):
    requester_or_ti(ticket_id); conn=get_db()
    ticket=conn.execute("SELECT t.*,u.name author FROM tickets t JOIN users u ON u.id=t.user_id WHERE t.id=?",(ticket_id,)).fetchone()
    comments=conn.execute("SELECT c.*,u.name,u.role FROM comments c JOIN users u ON u.id=c.user_id WHERE c.ticket_id=? ORDER BY c.created_at",(ticket_id,)).fetchall()
    events=conn.execute("SELECT e.*,u.name FROM ticket_events e LEFT JOIN users u ON u.id=e.user_id WHERE e.ticket_id=? ORDER BY e.created_at",(ticket_id,)).fetchall()
    related=conn.execute("SELECT id,title,status FROM tickets WHERE incident_key=? AND incident_key!='' AND id!=? AND status!='resolvido'",(ticket["incident_key"],ticket_id)).fetchall()
    techs=conn.execute("SELECT id,name FROM users WHERE role='ti'").fetchall()
    return render_template("ticket_detail.html",ticket=ticket,comments=comments,events=events,related=related,techs=techs)

@bp.post("/chamados/<int:ticket_id>/comentarios")
@login_required
def comment(ticket_id):
    requester_or_ti(ticket_id); body=request.form.get("body","").strip()
    if not 2<=len(body)<=2000: flash("A mensagem deve ter entre 2 e 2.000 caracteres.","erro")
    else:
        conn=get_db(); user=current_user(); stamp=now()
        conn.execute("INSERT INTO comments(ticket_id,user_id,body,created_at) VALUES(?,?,?,?)",(ticket_id,user["id"],body,stamp))
        status=conn.execute("SELECT status FROM tickets WHERE id=?",(ticket_id,)).fetchone()["status"]
        if user["role"]=="usuario" and status=="aguardando_usuario":
            conn.execute("UPDATE tickets SET status='em_atendimento',updated_at=? WHERE id=?",(stamp,ticket_id)); event(conn,ticket_id,user["id"],"status","Solicitante respondeu; voltou para atendimento")
        event(conn,ticket_id,user["id"],"comentario","Nova mensagem na conversa"); conn.commit(); flash("Mensagem adicionada à conversa.","sucesso")
    return redirect(url_for("tickets.detail",ticket_id=ticket_id)+"#conversa")

@bp.post("/chamados/<int:ticket_id>/atualizar")
@ti_required
def update(ticket_id):
    ticket=requester_or_ti(ticket_id); conn=get_db(); user=current_user(); status=request.form.get("status",""); priority=request.form.get("priority",ticket["priority"]); resolution=request.form.get("resolution","").strip(); assignee=request.form.get("assigned_to") or None
    if status not in STATUSES or priority not in PRIORITIES: abort(400)
    if status=="resolvido" and len(resolution)<5: flash("Inclua uma nota de conclusão com pelo menos 5 caracteres.","erro"); return redirect(url_for("tickets.detail",ticket_id=ticket_id))
    if status=="aguardando_usuario" and len(resolution)<5: flash("Escreva a informação que você precisa da pessoa solicitante.","erro"); return redirect(url_for("tickets.detail",ticket_id=ticket_id))
    stamp=now(); first=ticket["first_response_at"] or (stamp if status in {"em_atendimento","resolvido"} else None); resolved=stamp if status=="resolvido" else None
    conn.execute("UPDATE tickets SET status=?,priority=?,resolution=?,assigned_to=?,updated_at=?,first_response_at=?,resolved_at=? WHERE id=?",(status,priority,resolution if status=="resolvido" else "",assignee,stamp,first,resolved,ticket_id))
    if status=="aguardando_usuario":
        conn.execute("INSERT INTO comments(ticket_id,user_id,body,created_at) VALUES(?,?,?,?)",(ticket_id,user["id"],resolution,stamp))
    event(conn,ticket_id,user["id"],"atualizacao",f"Estado: {status}; prioridade: {priority}; atribuição: {assignee or 'sem responsável'}")
    if status!=ticket["status"]: event(conn,ticket_id,user["id"],"status",f"{ticket['status']} → {status}")
    conn.commit(); flash("Alteração registrada no histórico compartilhado.","sucesso"); return redirect(url_for("tickets.detail",ticket_id=ticket_id))

@bp.post("/chamados/<int:ticket_id>/feedback")
@login_required
def feedback(ticket_id):
    ticket=requester_or_ti(ticket_id); score=request.form.get("satisfaction",type=int); note=request.form.get("feedback","").strip()
    if current_user()["role"]!="usuario" or ticket["status"]!="resolvido": abort(403)
    if score not in range(1,6): flash("Escolha uma nota entre 1 e 5.","erro")
    else:
        conn=get_db(); conn.execute("UPDATE tickets SET satisfaction=?,feedback=? WHERE id=?",(score,note,ticket_id)); event(conn,ticket_id,current_user()["id"],"feedback",f"Avaliação: {score}/5 — {note}"); conn.commit(); flash("Obrigado pela avaliação.","sucesso")
    return redirect(url_for("tickets.detail",ticket_id=ticket_id))

@bp.post("/chamados/<int:ticket_id>/reabrir")
@login_required
def reopen(ticket_id):
    ticket=requester_or_ti(ticket_id)
    if current_user()["role"]!="usuario" or ticket["status"]!="resolvido": abort(403)
    conn=get_db()
    other=conn.execute("SELECT id FROM tickets WHERE user_id=? AND id!=? AND status!='resolvido' LIMIT 1",(current_user()["id"],ticket_id)).fetchone()
    if other:
        flash("Você já tem outro chamado em andamento; conclua-o antes de reabrir este.","erro")
        return redirect(url_for("tickets.detail",ticket_id=ticket_id))
    stamp=now(); conn.execute("UPDATE tickets SET status='aberto',resolution='',resolved_at=NULL,updated_at=? WHERE id=?",(stamp,ticket_id)); event(conn,ticket_id,current_user()["id"],"reaberto","Solicitante reabriu o chamado"); conn.commit(); flash("Chamado reaberto. A equipe foi informada no painel.","sucesso"); return redirect(url_for("tickets.detail",ticket_id=ticket_id))
