"""Memória do agente (SQLite).

Três papéis:
- turnos:     histórico de conversa por contato (memória de curto prazo)
- leads:      clientes interessados (para follow-up)
- escalacoes: casos que precisaram de humano

`cliente_recorrente` é um exemplo simples de memória de LONGO prazo:
antes de responder, olhamos o banco e injetamos contexto no agente.
"""
import sqlite3
from datetime import datetime, timezone

from . import config


def _conectar():
    config.BANCO.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.BANCO)
    con.execute("CREATE TABLE IF NOT EXISTS turnos(contato TEXT, role TEXT, content TEXT, ts TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS leads(nome TEXT, contato TEXT, interesse TEXT, ts TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS escalacoes(motivo TEXT, ts TEXT)")
    con.execute(
        "CREATE TABLE IF NOT EXISTS agendamentos("
        "nome TEXT, contato TEXT, servico TEXT, data TEXT, hora TEXT, valor REAL, ts TEXT)"
    )
    # Migração: bancos criados antes não têm a coluna 'domicilio'. Adiciona sem
    # recriar a tabela, preservando os agendamentos já existentes.
    colunas = {linha[1] for linha in con.execute("PRAGMA table_info(agendamentos)")}
    if "domicilio" not in colunas:
        con.execute("ALTER TABLE agendamentos ADD COLUMN domicilio INTEGER DEFAULT 0")
        con.commit()
    return con


def _agora():
    return datetime.now(timezone.utc).isoformat()


def carregar_historico(contato, limite=20):
    """Últimos `limite` turnos do contato, em ordem cronológica."""
    con = _conectar()
    linhas = con.execute(
        "SELECT role, content FROM turnos WHERE contato=? ORDER BY rowid DESC LIMIT ?",
        (contato, limite),
    ).fetchall()
    con.close()
    return [{"role": r, "content": c} for r, c in reversed(linhas)]


def salvar_turno(contato, role, content):
    con = _conectar()
    con.execute("INSERT INTO turnos VALUES(?,?,?,?)", (contato, role, content, _agora()))
    con.commit()
    con.close()


def salvar_lead(nome, contato, interesse):
    con = _conectar()
    con.execute("INSERT INTO leads VALUES(?,?,?,?)", (nome, contato, interesse, _agora()))
    con.commit()
    con.close()


def salvar_escalacao(motivo):
    con = _conectar()
    con.execute("INSERT INTO escalacoes VALUES(?,?)", (motivo, _agora()))
    con.commit()
    con.close()


def salvar_agendamento(nome, contato, servico, data, hora, valor, domicilio=False):
    con = _conectar()
    con.execute(
        "INSERT INTO agendamentos(nome,contato,servico,data,hora,valor,ts,domicilio)"
        " VALUES(?,?,?,?,?,?,?,?)",
        (nome, contato, servico, data, hora, valor, _agora(), int(bool(domicilio))),
    )
    con.commit()
    con.close()


def listar_agendamentos(limite=50):
    """Colunas explícitas — não quebra se a tabela ganhar novos campos."""
    con = _conectar()
    linhas = con.execute(
        "SELECT nome, contato, servico, data, hora, valor, domicilio, ts"
        " FROM agendamentos ORDER BY data, hora LIMIT ?",
        (limite,),
    ).fetchall()
    con.close()
    return linhas


def horarios_ocupados():
    """Conjunto de 'AAAA-MM-DD HH:MM' já reservados."""
    con = _conectar()
    linhas = con.execute("SELECT data, hora FROM agendamentos").fetchall()
    con.close()
    return {f"{d} {h}" for d, h in linhas}


def listar(tabela, limite=50):
    """Leitura genérica para o painel."""
    con = _conectar()
    linhas = con.execute(f"SELECT * FROM {tabela} ORDER BY rowid DESC LIMIT ?", (limite,)).fetchall()
    con.close()
    return linhas


def cliente_recorrente(contato):
    """True se o contato já virou lead alguma vez (memória de longo prazo)."""
    con = _conectar()
    (n,) = con.execute("SELECT COUNT(*) FROM leads WHERE contato=?", (contato,)).fetchone()
    con.close()
    return n > 0
