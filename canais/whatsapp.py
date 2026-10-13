"""Adaptador de WhatsApp — TEMPLATE (preencha quando escolher o provedor).

O ponto-chave: o cérebro NÃO muda. Quando o provedor (Evolution API, Z-API,
Cloud API) entregar uma mensagem no seu webhook, você chama core.processar()
— exatamente o mesmo que o terminal usa. Só o transporte é diferente.

Passos para plugar:
  1. Suba o provedor e aponte o webhook dele para o seu servidor (ex.: FastAPI).
  2. No handler do webhook, extraia (contato, texto) do payload DO SEU provedor.
  3. Chame `tratar_webhook(payload)`.
  4. Preencha `CanalWhatsApp.enviar` com a chamada HTTP de envio do provedor.
"""
import os

import httpx  # já vem instalado junto com o SDK anthropic

from agente import core

from .base import Canal


class CanalWhatsApp(Canal):
    def __init__(self):
        self.base_url = os.environ.get("WHATSAPP_API_URL", "")
        self.token = os.environ.get("WHATSAPP_API_TOKEN", "")

    def enviar(self, contato, texto):
        # TODO: adapte ao seu provedor. Exemplo genérico (Evolution/Z-API):
        # httpx.post(
        #     f"{self.base_url}/message/sendText",
        #     headers={"Authorization": f"Bearer {self.token}"},
        #     json={"number": contato, "text": texto},
        #     timeout=30,
        # )
        raise NotImplementedError(
            "Preencha CanalWhatsApp.enviar com a API de envio do seu provedor."
        )


def tratar_webhook(payload: dict) -> str:
    """Chame isto no endpoint HTTP quando o provedor entregar uma mensagem.

    Ajuste as duas linhas de extração ao formato do SEU provedor.
    """
    contato = payload["contato"]  # ex.: payload["data"]["key"]["remoteJid"]
    texto = payload["texto"]      # ex.: payload["data"]["message"]["conversation"]

    resposta = core.processar(contato, texto)  # <- o mesmo cérebro do terminal
    CanalWhatsApp().enviar(contato, resposta)
    return resposta
