"""Avisa o Moisés quando algo precisa dele.

Sem isto o funil termina num arquivo: o agente promete "vamos entrar em contato"
e ninguém fica sabendo. Aqui o aviso sai do banco e chega até você.

Backends (o primeiro que estiver configurado é usado, além do log):
  - arquivo : sempre — dados/avisos.log (padrão, zero configuração)
  - webhook : env AVISO_WEBHOOK_URL — dispara POST (WhatsApp, Telegram, Discord...)
"""
import json
import logging
import os
from datetime import datetime, timezone

from . import config

logger = logging.getLogger(__name__)

ARQUIVO = config.BASE_DIR / "dados" / "avisos.log"


def _escrever_arquivo(titulo, texto):
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).astimezone().strftime("%d/%m %H:%M")
    with open(ARQUIVO, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {titulo}\n{texto}\n{'-' * 50}\n")


def _enviar_webhook(titulo, texto):
    url = os.environ.get("AVISO_WEBHOOK_URL")
    if not url:
        return
    try:
        import httpx

        httpx.post(url, json={"titulo": titulo, "texto": texto}, timeout=10)
    except Exception as e:  # nunca deixe o aviso derrubar o atendimento
        logger.warning("falha ao enviar webhook de aviso: %s", e)


def avisar(titulo: str, texto: str):
    """Envia um aviso por todos os canais configurados. Nunca levanta exceção."""
    try:
        _escrever_arquivo(titulo, texto)
        _enviar_webhook(titulo, texto)
    except Exception as e:
        logger.warning("falha ao notificar: %s", e)
