"""Conexão, criação e migração incremental do SQLite."""
import sqlite3
from flask import current_app, g

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

def init_db(app):
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('usuario','ti')),username TEXT,email TEXT,password_hash TEXT,is_active INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL REFERENCES users(id),title TEXT NOT NULL,description TEXT NOT NULL,priority TEXT NOT NULL CHECK(priority IN ('baixa','media','alta','critica')),status TEXT NOT NULL DEFAULT 'aberto' CHECK(status IN ('aberto','em_atendimento','aguardando_usuario','resolvido')),created_at TEXT NOT NULL,updated_at TEXT NOT NULL,resolution TEXT NOT NULL DEFAULT '');
    CREATE TABLE IF NOT EXISTS comments(id INTEGER PRIMARY KEY AUTOINCREMENT,ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id),body TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS ticket_events(id INTEGER PRIMARY KEY AUTOINCREMENT,ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,user_id INTEGER REFERENCES users(id),event_type TEXT NOT NULL,details TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS knowledge_articles(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,category TEXT NOT NULL,keywords TEXT NOT NULL,body TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_tickets_status_created ON tickets(status,created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_comments_ticket ON comments(ticket_id,created_at);
    """)
    # Adiciona campos às bases criadas pela versão inicial, sem remover chamados existentes.
    existing = {row[1] for row in conn.execute("PRAGMA table_info(tickets)")}
    additions = {"category":"TEXT NOT NULL DEFAULT 'outros'", "system_name":"TEXT NOT NULL DEFAULT ''", "affected_count":"INTEGER NOT NULL DEFAULT 1", "business_impact":"TEXT NOT NULL DEFAULT 'medio'", "assigned_to":"INTEGER REFERENCES users(id)", "first_response_at":"TEXT", "resolved_at":"TEXT", "satisfaction":"INTEGER", "feedback":"TEXT NOT NULL DEFAULT ''", "incident_key":"TEXT NOT NULL DEFAULT ''"}
    for name, declaration in additions.items():
        if name not in existing: conn.execute(f"ALTER TABLE tickets ADD COLUMN {name} {declaration}")
    user_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    for name, declaration in {"username":"TEXT", "email":"TEXT", "password_hash":"TEXT", "is_active":"INTEGER NOT NULL DEFAULT 1"}.items():
        if name not in user_columns: conn.execute(f"ALTER TABLE users ADD COLUMN {name} {declaration}")
    schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='tickets'").fetchone()[0]
    if "aguardando_usuario" not in schema:
        conn.executescript("""
        CREATE TABLE tickets_migrated(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL REFERENCES users(id),title TEXT NOT NULL,description TEXT NOT NULL,priority TEXT NOT NULL CHECK(priority IN ('baixa','media','alta','critica')),status TEXT NOT NULL DEFAULT 'aberto' CHECK(status IN ('aberto','em_atendimento','aguardando_usuario','resolvido')),created_at TEXT NOT NULL,updated_at TEXT NOT NULL,resolution TEXT NOT NULL DEFAULT '',category TEXT NOT NULL DEFAULT 'outros',system_name TEXT NOT NULL DEFAULT '',affected_count INTEGER NOT NULL DEFAULT 1,business_impact TEXT NOT NULL DEFAULT 'medio',assigned_to INTEGER REFERENCES users(id),first_response_at TEXT,resolved_at TEXT,satisfaction INTEGER,feedback TEXT NOT NULL DEFAULT '',incident_key TEXT NOT NULL DEFAULT '');
        INSERT INTO tickets_migrated SELECT id,user_id,title,description,priority,CASE WHEN status='resolvido' THEN 'resolvido' ELSE status END,created_at,updated_at,resolution,category,system_name,affected_count,business_impact,assigned_to,first_response_at,resolved_at,satisfaction,feedback,incident_key FROM tickets;
        DROP TABLE tickets;
        ALTER TABLE tickets_migrated RENAME TO tickets;
        CREATE INDEX IF NOT EXISTS idx_tickets_status_created ON tickets(status,created_at DESC);
        """)
    # Desativa e anonimiza os quatro perfis de demonstração da versão anterior,
    # mantendo os IDs para preservar o vínculo com chamados já existentes.
    conn.execute("UPDATE users SET name='Conta migrada ' || id, username=NULL, email=NULL, password_hash=NULL, is_active=0 WHERE username IS NULL AND password_hash IS NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username COLLATE NOCASE) WHERE username IS NOT NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email COLLATE NOCASE) WHERE email IS NOT NULL")
    articles = [
      ("Reconectar ao Wi-Fi corporativo","rede","wifi internet sem fio conexão rede","Confira se o modo avião está desligado, reconecte à rede corporativa e reinicie o adaptador. Se outros usuários também estiverem sem conexão, informe isso no chamado."),
      ("Redefinir acesso e senha","acesso","senha login acesso bloqueado conta autenticação","Confirme se o usuário está correto e tente redefinir a senha pelo portal corporativo. Nunca compartilhe sua senha no chamado."),
      ("Impressora sem responder","impressora","impressora impressão fila papel toner","Confira energia, papel e conexão. Verifique se a impressora correta está selecionada e se há trabalhos travados na fila."),
      ("Aplicativo lento ou indisponível","sistema","sistema aplicativo lento erro travado vendas","Registre o nome do sistema, horário do erro e se colegas são afetados. Tente sair e entrar novamente; não repita operações financeiras."),
    ]
    conn.executemany("INSERT INTO knowledge_articles(title,category,keywords,body) SELECT ?,?,?,? WHERE NOT EXISTS(SELECT 1 FROM knowledge_articles WHERE title=?)", [(a,b,c,d,a) for a,b,c,d in articles])
    conn.commit(); conn.execute("PRAGMA foreign_keys=ON"); conn.close()
