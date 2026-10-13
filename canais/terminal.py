"""Canal de terminal — para testar o agente localmente, sem WhatsApp."""
from .base import Canal


class CanalTerminal(Canal):
    def enviar(self, contato, texto):
        print(f"\nabdalla > {texto}\n")
