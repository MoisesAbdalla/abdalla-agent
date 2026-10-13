"""Mede o custo real de uma conversa típica de venda. Rode: .\\custo.cmd

Use isto para planejar: quanto custa atender N clientes por mês.
"""
import os

# não sujar o banco de produção com esta simulação
os.environ.setdefault("ABDALLA_BANCO", "dados/custo_teste.db")

from agente import config, core  # noqa: E402

# Conversa realista de venda, do "oi" ao lead registrado.
CONVERSA = [
    "ola, gostaria de consultar valores de servicos",
    "queria fazer uma limpeza + troca de pasta termica",
    "quanto tempo demora?",
    "quero sim, meu nome e Carlos e telefone 16999990000",
]


def main():
    print(f"modelo: {config.MODELO}\n")
    historico = []
    entrada = saida = c_esc = c_lei = 0

    for i, msg in enumerate(CONVERSA, 1):
        historico.append({"role": "user", "content": msg})
        r = core.responder(historico)
        historico.append({"role": "assistant", "content": r.texto})
        entrada += r.tokens_entrada
        saida += r.tokens_saida
        c_esc += r.cache_escrita
        c_lei += r.cache_leitura
        print(
            f"turno {i}: {r.tokens_entrada:>5} in | {r.tokens_saida:>4} out | "
            f"cache {r.cache_escrita:>5}w/{r.cache_leitura:>5}r | US$ {r.custo_usd:.5f}"
        )

    total = core.Resposta("", [], entrada, saida, c_esc, c_lei)
    custo = total.custo_usd
    print(f"\n{'='*68}")
    print(f"CONVERSA COMPLETA ({len(CONVERSA)} turnos)")
    print(f"  tokens        : {entrada} entrada / {saida} saida")
    print(f"  cache         : {c_esc} gravados / {c_lei} lidos (lido custa 10%)")
    print(f"  custo         : US$ {custo:.5f}")
    print(f"{'='*68}")
    print("\nPROJEÇÃO (conversas por mês -> custo mensal):")
    for n in (100, 500, 1000, 3000):
        print(f"  {n:>5} conversas : US$ {custo*n:>7.2f}")


if __name__ == "__main__":
    main()
