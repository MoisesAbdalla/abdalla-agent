"""Confere o catálogo de serviços SEM chamar a API. Custo: R$ 0,00.

Use sempre que editar SERVICOS em agente/config.py. Pega erro de estrutura,
campo faltando e incoerência de regra de negócio antes de você gastar crédito
rodando os evals.

Rode: .\\validar.cmd
"""
from agente import config

OBRIGATORIOS = ("nome", "duracao_h", "prazo", "inclui")

erros = []
avisos = []


def erro(msg):
    erros.append(msg)


def aviso(msg):
    avisos.append(msg)


def checar_servico(chave, item):
    ctx = f"'{chave}'"

    if not isinstance(item, dict):
        return erro(f"{ctx}: deveria ser um dicionário")

    for campo in OBRIGATORIOS:
        if not item.get(campo):
            erro(f"{ctx}: falta o campo obrigatório '{campo}'")

    if not item.get("categoria"):
        aviso(f"{ctx}: sem 'categoria' — use 'pc' ou 'impressora' para agrupar o catálogo")

    formas = [f for f in ("preco", "variantes", "preco_minimo") if f in item]
    if not formas:
        erro(f"{ctx}: precisa de 'preco', 'variantes' OU 'preco_minimo'")
    if len(formas) > 1:
        erro(f"{ctx}: use apenas uma forma de preço (tem: {', '.join(formas)})")

    tem_preco = "preco" in item
    tem_var = "variantes" in item

    if "preco_minimo" in item:
        p = item["preco_minimo"]
        if not isinstance(p, (int, float)) or p <= 0:
            erro(f"{ctx}: 'preco_minimo' deve ser maior que zero (está: {p!r})")

    if tem_preco:
        p = item["preco"]
        if not isinstance(p, (int, float)) or p < 0:
            erro(f"{ctx}: 'preco' deve ser um número não negativo (está: {p!r})")
        elif p > config.VALOR_MAX_AUTONOMO:
            aviso(f"{ctx}: R$ {p} passa do teto autônomo (R$ {config.VALOR_MAX_AUTONOMO}) "
                  f"— o agente vai te escalar toda venda deste serviço")

    if tem_var:
        variantes = item["variantes"]
        if not isinstance(variantes, dict) or not variantes:
            erro(f"{ctx}: 'variantes' deve ser um dicionário não vazio")
        else:
            for nome_v, v in variantes.items():
                cv = f"{ctx} variante '{nome_v}'"
                if not isinstance(v, dict):
                    erro(f"{cv}: deveria ser um dicionário")
                    continue
                p = v.get("preco")
                if not isinstance(p, (int, float)) or p <= 0:
                    erro(f"{cv}: 'preco' deve ser um número maior que zero (está: {p!r})")
                elif p > config.VALOR_MAX_AUTONOMO:
                    aviso(f"{cv}: R$ {p} passa do teto autônomo "
                          f"(R$ {config.VALOR_MAX_AUTONOMO})")
                if not v.get("quando"):
                    erro(f"{cv}: falta 'quando' — é o que ensina o agente a escolher "
                         f"a variante certa")

    d = item.get("duracao_h")
    if d is not None and (not isinstance(d, (int, float)) or d <= 0):
        erro(f"{ctx}: 'duracao_h' deve ser um número maior que zero (está: {d!r})")


def main():
    print("\nVALIDANDO CATÁLOGO (sem usar a API)\n" + "=" * 60)

    if not config.SERVICOS:
        erro("SERVICOS está vazio")

    for chave, item in config.SERVICOS.items():
        if not chave.islower() or " " in chave:
            aviso(f"'{chave}': prefira chave minúscula e sem espaço (ex.: revisao_gpu)")
        checar_servico(chave, item)

    if config.TAXA_DIAGNOSTICO_SEM_SERVICO is None:
        aviso("TAXA_DIAGNOSTICO_SEM_SERVICO ainda é None — o agente vai dizer que existe "
              "taxa mas escalar quando perguntarem o valor. Defina quando decidir.")

    # Visão geral do que o agente vai saber, agrupado por categoria
    print(f"\n{len(config.SERVICOS)} serviços no catálogo:")
    por_cat = {}
    for chave, item in config.SERVICOS.items():
        por_cat.setdefault(item.get("categoria", "sem categoria"), []).append((chave, item))

    for cat, itens in por_cat.items():
        print(f"\n  [{cat}]")
        for chave, item in itens:
            if "variantes" in item:
                valor = "/".join(f"R$ {v['preco']:.0f}" for v in item["variantes"].values())
            elif "preco_minimo" in item:
                valor = f"a partir de R$ {item['preco_minimo']:.0f}"
            elif item.get("preco") == 0:
                valor = "gratuito"
            else:
                valor = f"R$ {item.get('preco', 0):.0f}"
            print(f"    {chave:<26} {item.get('nome','?'):<42} {valor}")

    print(f"\nAlçada: desconto até {config.DESCONTO_MAX_PCT}% "
          f"({config.DESCONTO_COMBO_PCT}% em combo) | teto autônomo R$ {config.VALOR_MAX_AUTONOMO}")

    print("\n" + "=" * 60)
    for a in avisos:
        print(f"  AVISO: {a}")
    for e in erros:
        print(f"  ERRO : {e}")

    if erros:
        print(f"\n{len(erros)} erro(s) — corrija antes de rodar os evals.\n")
        return 1
    print(f"\nCatálogo OK{f' ({len(avisos)} aviso(s))' if avisos else ''}. "
          f"Pode rodar .\\evals.cmd quando quiser.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
