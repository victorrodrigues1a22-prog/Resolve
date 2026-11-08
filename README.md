# Resolve — central de chamados de TI

Aplicação web em Python, Flask e SQLite para organizar solicitações internas de suporte.

## Executar no Windows / VS Code

Abra a pasta do projeto no VS Code e rode no terminal:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Acesse http://127.0.0.1:5000. O banco local `chamados.db` é criado automaticamente.

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

## Privacidade e implantação

O banco SQLite local está ignorado pelo Git e não deve ser publicado. Na atualização, as antigas contas de demonstração são anonimizadas sem apagar os chamados vinculados. O texto livre de chamados/comentários pode conter dados pessoais inseridos pelos usuários; revise esses registros antes de usar ou compartilhar uma cópia do banco. Antes de publicar o serviço, configure `SECRET_KEY` aleatória, HTTPS, proteção CSRF, limitação de tentativas de login, backups e provedor real de notificações. O servidor Flask embutido é apenas para desenvolvimento.
