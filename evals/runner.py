"""Roda os evals. Uso (a partir da pasta do projeto):  python -m evals.runner

Mistura duas técnicas:
  - checagem determinística: a tool certa foi chamada? o texto contém X?
  - LLM-como-juiz: outro modelo (barato) avalia respostas subjetivas.
"""
import logging
import os
import sys

# Sem isto, uma falha de API vira a mensagem de fallback e você nunca descobre
# o motivo — o eval acusa "resposta errada" quando o problema foi rede/limite.
logging.basicConfig(level=logging.WARNING, format="  [LOG] %(levelname)s: %(message)s")

# Evals NUNCA podem escrever no banco de produção — senão leads de teste
# (João, Ana...) se misturam com clientes reais. Definido ANTES de importar
# o agente, porque config lê a env no import.
os.environ.setdefault("ABDALLA_BANCO", str(
    __import__("pathlib").Path(__file__).resolve().parent.parent / "dados" / "evals.db"
))

from anthropic import Anthropic  # noqa: E402

from agente import config, core  # noqa: E402
from evals.casos import CASOS  # noqa: E402

_cliente = None

# O JUIZ precisa ser bom. Com claude-haiku-4-5 tivemos falhas fantasma: ele reprovava
# respostas corretas (ex.: uma recusa explícita de desconto), o que faz você "consertar"
# um agente que não estava quebrado. Juiz fraco é pior que juiz nenhum.
MODELO_JUIZ = "claude-sonnet-5"


def _juiz(pergunta, resposta):
    global _cliente
    if _cliente is None:
        _cliente = Anthropic()
    r = _cliente.messages.create(
        model=MODELO_JUIZ,
        max_tokens=10,
        system="Você avalia a resposta de um atendente. Responda APENAS 'SIM' ou 'NAO'.",
        messages=[{
            "role": "user",
            "content": f"Critério: {pergunta}\n\nResposta avaliada:\n{resposta}\n\nO critério foi atendido?",
        }],
    )
    txt = "".join(b.text for b in r.content if b.type == "text").upper()
    return "SIM" in txt


def rodar_caso(caso):
    historico = []
    tools_chamadas = []
    respostas = []
    for msg in caso["mensagens"]:
        historico.append({"role": "user", "content": msg})
        resp = core.responder(historico)
        historico.append({"role": "assistant", "content": resp.texto})
        tools_chamadas += resp.tools_chamadas
        respostas.append(resp.texto)

    ultima = respostas[-1] if respostas else ""
    conversa = "\n".join(respostas)  # o agente pode ter dito o que queremos em turno anterior

    falhas = []
    if caso.get("espera_tool") and caso["espera_tool"] not in tools_chamadas:
        falhas.append(f"esperava tool '{caso['espera_tool']}' (chamadas: {tools_chamadas or 'nenhuma'})")
    for t in caso.get("nao_espera_tool", []):
        if t in tools_chamadas:
            falhas.append(f"tool '{t}' NÃO deveria ter sido chamada")
    # texto: procuramos em TODA a conversa, não só no último turno
    for sub in caso.get("espera_no_texto", []):
        if sub.lower() not in conversa.lower():
            falhas.append(f"texto deveria conter '{sub}' em algum turno")
    # juiz: recebe a CONVERSA INTEIRA. Julgar só o último turno reprovava casos
    # corretos, porque o comportamento avaliado pode ter ocorrido antes (ex.: a
    # recusa acontece no turno 2 e o turno 3 apenas escala).
    if caso.get("juiz") and not _juiz(caso["juiz"], conversa):
        falhas.append(f"juiz reprovou: {caso['juiz']}")
    return falhas, ultima


def main():
    print(f"Rodando {len(CASOS)} casos | modelo: {config.MODELO}\n")
    reprovados = 0
    for caso in CASOS:
        falhas, ultima = rodar_caso(caso)
        if falhas:
            reprovados += 1
            print(f"[FALHOU] {caso['id']}")
            for f in falhas:
                print(f"    - {f}")
            print(f"    resposta: {ultima[:120]}")
        else:
            print(f"[OK]     {caso['id']}")
    print(f"\n{len(CASOS) - reprovados}/{len(CASOS)} passaram.")
    sys.exit(1 if reprovados else 0)


if __name__ == "__main__":
    main()
