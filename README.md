# Resolve — central de chamados de TI

Aplicação web em Python, Flask e SQLite para organizar solicitações internas de suporte.

## Executar no Windows / VS Code

Abra a pasta do projeto no VS Code e rode no terminal:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Acesse http://127.0.0.1:5000. O banco local `chamados.db` é criado automaticamente.

## Implantar no Render

Para um **Web Service** conectado a este repositório, configure:

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`

O comando local do Windows (`.venv\Scripts\python.exe app.py`) não funciona no Render, que executa Linux. Defina também `SECRET_KEY` como variável de ambiente secreta no painel do Render. O Render inicia uma nova implantação quando esta correção chegar à branch `main`.

> **Persistência:** este projeto usa SQLite em `chamados.db`. O disco padrão dos serviços Render pode ser efêmero; dados podem ser perdidos em reinicializações ou novas implantações. Para guardar contas e chamados de forma durável, configure um disco persistente compatível com seu plano ou migre para PostgreSQL antes de uso real.

## Contas e acesso

- Solicitantes criam sua própria conta em **Criar conta**. O cadastro pede nome, usuário, e-mail e senha de pelo menos 12 caracteres.
- A senha é guardada como hash seguro com Werkzeug; o sistema nunca armazena a senha em texto simples. O login aceita nome de usuário ou e-mail.
- Cadastro público sempre cria perfil de solicitante. Para provisionar alguém da equipe de TI, execute `python -m support.create_ti` e siga as perguntas no terminal. Não existe seleção de papel privilegiado na tela pública.
- Os perfis fictícios da demonstração anterior são desativados e seus nomes substituídos por identificadores genéricos durante a migração. Os chamados antigos continuam associados a essas contas anonimizadas.

## Funcionalidades

- Abertura de chamado com triagem guiada por categoria, sistema, impacto e quantidade de pessoas afetadas.
- Base pesquisável de orientações rápidas antes de registrar a solicitação.
- Fila de TI com filtros, atribuição de responsável e ordenação por prioridade, alcance e impacto.
- Comentários no chamado, estado “Aguardando você” e retorno ao atendimento quando o solicitante responde.
- Histórico de mudanças, possíveis chamados relacionados, métricas de atendimento, avaliação e reabertura.

## Organização do código

```text
app.py                      inicialização
support/__init__.py         fábrica e configuração Flask
support/db.py               SQLite e migrações
support/auth.py             autorização por perfil
support/create_ti.py        criação segura de conta técnica
support/routes/auth.py      cadastro e login
support/routes/dashboard.py painéis
support/routes/tickets.py   chamados, conversa e histórico
templates/                  uma página por tela
static/                     estilos
```

As páginas usam `extends` para compartilhar o cabeçalho e a estrutura comum. Cada tela e cada conjunto de rotas permanece em arquivo próprio.

## Aviso para quem clonar ou implantar este projeto

**Antes de usar este sistema com pessoas ou dados reais, leia estes cuidados:**

- O arquivo `chamados.db` contém contas, chamados e conversas. Ele é ignorado pelo Git de propósito: não o adicione nem envie ao repositório. Faça cópias de segurança em local protegido.
- Descrições e comentários são texto livre e podem incluir dados pessoais. Revise e remova essas informações antes de compartilhar uma cópia do banco. A migração anonimiza os nomes das antigas contas de demonstração, mas preserva os chamados e não apaga informações pessoais digitadas no conteúdo.
- Defina uma `SECRET_KEY` forte e exclusiva no ambiente antes de disponibilizar o serviço. Não publique essa chave nem credenciais no código ou no Git.
- O cadastro aberto cria apenas contas de solicitante. Crie contas da equipe de TI pelo comando `python -m support.create_ti` e limite esse acesso às pessoas autorizadas.
- Esta versão ainda precisa de proteção CSRF, limite de tentativas de login, HTTPS, backups protegidos e configuração de um servidor WSGI de produção. O servidor iniciado por `python app.py` é destinado somente ao desenvolvimento local.
