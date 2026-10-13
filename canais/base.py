"""Interface de canal. Todo canal (terminal, WhatsApp, Instagram...) implementa `enviar`.

A ENTRADA de mensagem é específica de cada canal:
- terminal: lê do teclado (pull)
- WhatsApp: recebe via webhook HTTP (push)

Em ambos os casos o cérebro é o mesmo: core.processar(contato, texto).
"""
from abc import ABC, abstractmethod


class Canal(ABC):
    @abstractmethod
    def enviar(self, contato: str, texto: str) -> None:
        """Envia uma resposta de volta ao contato."""
        ...
