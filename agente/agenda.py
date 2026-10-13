"""Agenda de serviços: horários livres e reservas.

Decisão de design: o agente NÃO recebe a data de hoje no prompt (isso quebraria o
prompt caching, que exige prefixo idêntico). Em vez disso, a tool devolve as datas
já calculadas e com o dia da semana escrito — o agente só precisa ler.
"""
from datetime import date, datetime, timedelta

from . import config, memoria

# Seg=0 ... Dom=6 -> faixas de horário de atendimento
EXPEDIENTE = {
    0: (9, 18), 1: (9, 18), 2: (9, 18), 3: (9, 18), 4: (9, 18),  # seg-sex
    5: (9, 13),                                                   # sábado
}

DIAS_PT = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _slots_do_dia(dia: date):
    faixa = EXPEDIENTE.get(dia.weekday())
    if not faixa:
        return []
    inicio, fim = faixa
    return [f"{h:02d}:00" for h in range(inicio, fim)]


def horarios_livres(dias_a_frente: int = 7, limite: int = 8):
    """Próximos horários disponíveis, já descontando o que está reservado."""
    ocupados = memoria.horarios_ocupados()
    livres = []
    hoje = date.today()

    for delta in range(1, dias_a_frente + 1):  # a partir de amanhã
        dia = hoje + timedelta(days=delta)
        for hora in _slots_do_dia(dia):
            chave = f"{dia.isoformat()} {hora}"
            if chave in ocupados:
                continue
            livres.append({
                "data": dia.isoformat(),
                "hora": hora,
                "dia_semana": DIAS_PT[dia.weekday()],
                "rotulo": f"{DIAS_PT[dia.weekday()]} {dia.strftime('%d/%m')} às {hora}",
            })
            if len(livres) >= limite:
                return livres
    return livres


def validar(data_iso: str, hora: str):
    """Devolve (ok, motivo). Valida formato, expediente e disponibilidade."""
    try:
        dia = datetime.strptime(data_iso, "%Y-%m-%d").date()
    except ValueError:
        return False, "Data inválida. Use o formato AAAA-MM-DD."

    if dia <= date.today():
        return False, "Só é possível agendar a partir de amanhã."
    if hora not in _slots_do_dia(dia):
        return False, f"Fora do expediente. {config.NEGOCIO['horario']}"
    if f"{data_iso} {hora}" in memoria.horarios_ocupados():
        return False, "Esse horário já está reservado."
    return True, ""
