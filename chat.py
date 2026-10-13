"""Converse com o agente no terminal. Rode: python chat.py"""
from agente import core
from canais.terminal import CanalTerminal

CONTATO = "terminal-teste"


def main():
    canal = CanalTerminal()
    print("Agente Abdalla Tech — digite 'sair' para encerrar.\n")
    while True:
        try:
            texto = input("você > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if texto.lower() in ("sair", "exit", "quit"):
            break
        if not texto:
            continue
        resposta = core.processar(CONTATO, texto)
        canal.enviar(CONTATO, resposta)


if __name__ == "__main__":
    main()
