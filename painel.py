"""Painel do Moisés: o que o agente produziu. Rode: .\\painel.cmd

Custo: R$ 0,00 — lê o banco local, não chama a API.
"""
from datetime import date, datetime

from agente import memoria


def _dia(ts):
    try:
        return datetime.fromisoformat(ts).astimezone().strftime("%d/%m %H:%M")
    except Exception:
        return ts


def secao(titulo):
    print(f"\n{'=' * 62}\n  {titulo}\n{'=' * 62}")


def main():
    hoje = date.today().isoformat()

    secao("AGENDAMENTOS CONFIRMADOS")
    ags = memoria.listar_agendamentos()
    if not ags:
        print("  (nenhum)")
    for nome, contato, servico, data, hora, valor, domicilio, ts in ags:
        marca = " <-- HOJE" if data == hoje else ""
        local = "DOMICILIO" if domicilio else "loja"
        print(f"  {data} {hora} | {nome:<16} {contato:<14} {servico:<24} "
              f"R$ {valor:>7.2f} | {local}{marca}")

    secao("PRECISAM DE VOCÊ (escalações)")
    esc = memoria.listar("escalacoes")
    if not esc:
        print("  (nenhuma) — o agente resolveu tudo sozinho")
    for motivo, ts in esc:
        print(f"  {_dia(ts)} | {motivo}")

    secao("LEADS (interessados que ainda não agendaram)")
    agendados = {(linha[0], linha[1]) for linha in ags}
    leads = memoria.listar("leads")
    pendentes = [l for l in leads if (l[0], l[1]) not in agendados]
    if not pendentes:
        print("  (nenhum pendente)")
    for nome, contato, interesse, ts in pendentes:
        print(f"  {_dia(ts)} | {nome:<18} {contato:<15} {interesse}")

    print(f"\n{'=' * 62}")
    print(f"  {len(ags)} agendados | {len(pendentes)} leads a converter | {len(esc)} p/ você")
    print(f"{'=' * 62}\n")


if __name__ == "__main__":
    main()
