"""As "mãos" do agente: tools que o Claude pode chamar.

Cada tool registra a própria chamada num contextvar. Isso permite que os
EVALS verifiquem "a tool certa foi chamada?" — e é seguro para concorrência
(cada request tem sua própria lista isolada).
"""
import contextvars
import json

from anthropic import beta_tool

from . import agenda, config, memoria, notificacoes

_chamadas: contextvars.ContextVar = contextvars.ContextVar("_chamadas", default=None)


def iniciar_registro():
    """Zera e devolve a lista de tools chamadas neste request."""
    lista = []
    _chamadas.set(lista)
    return lista


def _registrar(nome):
    lista = _chamadas.get()
    if lista is not None:
        lista.append(nome)


@beta_tool
def orcamento_servico(servico: str, variante: str = "") -> str:
    """Consulta o preço oficial de um serviço da Abdalla Tech.

    Chame esta tool sempre que o cliente perguntar quanto custa, pedir orçamento, citar valor,
    ou demonstrar interesse em um serviço — mesmo que você ache que sabe o preço. Esta é a
    única fonte de preço válida; responder de memória é erro.

    Alguns serviços têm variantes de preço (ex.: revisao_gpu é 'low' ou 'high' conforme o
    modelo da placa). Se não souber qual, pergunte ao cliente qual a placa antes de cotar.

    Args:
        servico: chave do serviço: limpeza, revisao_gpu, montagem, upgrade_ssd, diagnostico.
        variante: quando o serviço tiver variantes (ex.: 'low' ou 'high' em revisao_gpu).
    """
    _registrar("orcamento_servico")
    item = config.SERVICOS.get(servico)
    if not item:
        return f"Serviço '{servico}' não encontrado. Opções: {', '.join(config.SERVICOS)}"

    preco = config.preco_de(servico, variante)
    if preco is None:
        # Serviço com variantes e nenhuma (ou inválida) informada: devolve as opções
        # em vez de chutar um preço.
        opcoes = {n: {"preco": v["preco"], "quando": v["quando"]}
                  for n, v in item["variantes"].items()}
        return json.dumps(
            {"precisa_variante": True, "servico": servico, "opcoes": opcoes,
             "instrucao": "Descubra o modelo da placa com o cliente e chame de novo "
                          "informando a variante."},
            ensure_ascii=False,
        )

    resposta = {
        "servico": servico,
        "nome": item["nome"] + (f" ({variante})" if variante else ""),
        "prazo": item["prazo"],
        "duracao_horas": item["duracao_h"],
        "inclui": item["inclui"],
    }

    if config.preco_aberto(servico):
        # Serviço "a partir de": informar piso e proibir promessa de valor fechado.
        resposta.update({
            "tipo_preco": "a_partir_de",
            "preco_minimo_reais": preco,
            "instrucao": f"Diga 'a partir de R$ {preco:.0f}'. O valor final depende do "
                         f"defeito e é confirmado com o cliente após a avaliação. NÃO "
                         f"prometa preço fechado e NÃO conceda desconto sobre este serviço.",
        })
    elif preco == 0:
        resposta.update({
            "tipo_preco": "gratuito",
            "preco_reais": 0,
            "instrucao": "Diagnóstico gratuito quando o cliente realiza o serviço. "
                         "Se ele não realizar, há taxa (ver política no seu prompt).",
        })
    else:
        resposta.update({
            "tipo_preco": "fechado",
            "preco_reais": preco,
            # Alçada calculada: o agente não precisa fazer conta de cabeça.
            "desconto_max_pct": config.DESCONTO_MAX_PCT,
            "preco_minimo_autorizado": round(preco * (1 - config.DESCONTO_MAX_PCT / 100), 2),
            "obs": "Você pode fechar dentro deste limite sem consultar ninguém.",
        })

    if item.get("nao_inclui"):
        resposta["nao_inclui"] = item["nao_inclui"]
    return json.dumps(resposta, ensure_ascii=False)


@beta_tool
def consultar_horarios(dias_a_frente: int = 7) -> str:
    """Lista os próximos horários livres na agenda, com data e dia da semana prontos.

    Chame esta tool quando o cliente quiser marcar, perguntar sobre disponibilidade ou
    quando você for propor um horário. Nunca invente datas nem diga "amanhã" sem
    consultar — só esta tool sabe o que está livre.

    Args:
        dias_a_frente: quantos dias à frente procurar (padrão 7).
    """
    _registrar("consultar_horarios")
    livres = agenda.horarios_livres(dias_a_frente=dias_a_frente)
    if not livres:
        return "Nenhum horário livre nesse período. Tente um intervalo maior."
    return json.dumps(
        {"horarios_livres": [h["rotulo"] for h in livres],
         "formato_para_agendar": [{"data": h["data"], "hora": h["hora"]} for h in livres]},
        ensure_ascii=False,
    )


@beta_tool
def agendar_servico(nome: str, contato: str, servico: str, data: str, hora: str,
                    valor_final: float, variante: str = "", domicilio: bool = False) -> str:
    """Reserva o horário e fecha o serviço. Esta tool CONCLUI a venda.

    Chame quando o cliente aceitar um horário. Valide antes com consultar_horarios.
    O valor_final é o preço acordado — pode incluir o desconto que você concedeu
    dentro da sua alçada, mas nunca abaixo do preco_minimo_autorizado do orçamento.

    Args:
        nome: nome do cliente.
        contato: telefone/WhatsApp do cliente.
        servico: chave do serviço (limpeza, revisao_gpu, montagem, upgrade_ssd, diagnostico).
        data: data no formato AAAA-MM-DD.
        hora: hora no formato HH:MM.
        valor_final: TOTAL acordado em reais, já incluindo a taxa de domicílio se houver.
        variante: quando o serviço tiver variantes (ex.: 'low'/'high' em revisao_gpu).
        domicilio: True se o atendimento for na casa do cliente (soma a taxa de domicílio).
    """
    _registrar("agendar_servico")

    item = config.SERVICOS.get(servico)
    if not item:
        return f"Serviço '{servico}' não existe. Opções: {', '.join(config.SERVICOS)}"

    tabela = config.preco_de(servico, variante)
    if tabela is None:
        return (f"NÃO AGENDADO: '{servico}' exige variante "
                f"({', '.join(item['variantes'])}). Descubra com o cliente e agende de novo.")

    # A taxa de domicílio entra por fora e NÃO recebe desconto.
    extra = config.TAXA_DOMICILIO if domicilio else 0

    if config.preco_aberto(servico):
        # "A partir de": nada de desconto sobre valor ainda indefinido.
        if valor_final < tabela + extra:
            return (f"RECUSADO: {servico} é 'a partir de R$ {tabela:.2f}'"
                    + (f" + R$ {extra:.2f} de domicílio" if extra else "")
                    + f", total mínimo R$ {tabela + extra:.2f}. Agende pelo piso e explique "
                      f"que o valor final sai após a avaliação.")
    else:
        minimo = tabela * (1 - config.DESCONTO_MAX_PCT / 100) + extra
        if valor_final < minimo:
            return (f"RECUSADO: R$ {valor_final:.2f} está abaixo da sua alçada "
                    f"(mínimo R$ {minimo:.2f}"
                    + (f", já contando R$ {extra:.2f} de domicílio" if extra else "")
                    + "). Use escalar_humano para aprovar.")

    ok, motivo = agenda.validar(data, hora)
    if not ok:
        return f"NÃO AGENDADO: {motivo} Chame consultar_horarios e ofereça outro."

    rotulo = servico + (f":{variante}" if variante else "")
    memoria.salvar_agendamento(nome, contato, rotulo, data, hora, valor_final, domicilio)
    notificacoes.avisar(
        "AGENDAMENTO CONFIRMADO",
        f"{nome} ({contato})\n{item['nome']}"
        + (f" ({variante})" if variante else "")
        + f"\n{data} às {hora} — R$ {valor_final:.2f}"
        + ("\nLOCAL: EM DOMICÍLIO" if domicilio else "\nLocal: na loja"),
    )
    return json.dumps(
        {"status": "confirmado", "servico": item["nome"], "data": data, "hora": hora,
         "valor_total": valor_final, "em_domicilio": domicilio},
        ensure_ascii=False,
    )


@beta_tool
def registrar_lead(nome: str, contato: str, interesse: str) -> str:
    """Salva o cliente interessado no banco para follow-up do Moisés.

    Chame esta tool NO MESMO turno em que o cliente informar nome e telefone/WhatsApp.
    Não espere ele confirmar o serviço nem responder mais perguntas — sem esta chamada o
    lead é perdido. Se ainda não souber o interesse exato, use o assunto da conversa.

    Args:
        nome: nome do cliente.
        contato: telefone/WhatsApp do cliente.
        interesse: serviço ou dúvida principal do cliente.
    """
    _registrar("registrar_lead")
    memoria.salvar_lead(nome, contato, interesse)
    notificacoes.avisar("NOVO LEAD", f"{nome} ({contato})\nInteresse: {interesse}")
    return "Lead registrado com sucesso."


@beta_tool
def escalar_humano(motivo: str) -> str:
    """Notifica o Moisés (humano) de que esta conversa precisa dele.

    ESCALAR É EXCEÇÃO, NÃO ROTINA. Você resolve sozinho desconto dentro da alçada,
    agendamento e dúvidas sobre o negócio. Chame esta tool apenas quando: o desconto pedido
    passar do seu limite, o valor passar do teto autônomo, houver reclamação/defeito/problema,
    ou for um caso realmente fora do padrão. Chame ANTES de dizer que vai encaminhar.

    Args:
        motivo: por que a conversa precisa de um humano.
    """
    _registrar("escalar_humano")
    memoria.salvar_escalacao(motivo)
    notificacoes.avisar("PRECISA DE VOCÊ", motivo)
    return "Encaminhei para um atendente humano; ele responde em instantes."


TOOLS = [
    orcamento_servico,
    consultar_horarios,
    agendar_servico,
    registrar_lead,
    escalar_humano,
]
