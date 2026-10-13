"""O cérebro do agente — independente de canal.

`responder`  -> recebe o histórico, roda o loop do Claude (pensa->age->observa)
                e devolve texto + quais tools foram chamadas (para os evals).
`processar`  -> ponto de entrada usado por qualquer canal (terminal, WhatsApp):
                cuida da memória e delega para `responder`.
"""
import logging
from dataclasses import dataclass, field

from anthropic import Anthropic, APIError

from . import config, memoria, tools

logger = logging.getLogger(__name__)

_cliente = None

# Rede de segurança: o cliente NUNCA pode receber silêncio.
FALLBACK = "Opa, deu um probleminha aqui do meu lado. Pode repetir, por favor?"


def _get_cliente():
    global _cliente
    if _cliente is None:
        _cliente = Anthropic()  # lê ANTHROPIC_API_KEY do ambiente
    return _cliente


@dataclass
class Resposta:
    texto: str
    tools_chamadas: list = field(default_factory=list)
    tokens_entrada: int = 0
    tokens_saida: int = 0
    cache_escrita: int = 0  # gravados no cache (~1.25x o preço de entrada)
    cache_leitura: int = 0  # servidos do cache (~0.1x o preço de entrada)

    @property
    def custo_usd(self):
        p = config.PRECOS_USD.get(config.MODELO)
        if not p:
            return 0.0
        e = p["entrada"] / 1e6
        return (
            self.tokens_entrada * e
            + self.cache_escrita * e * 1.25
            + self.cache_leitura * e * 0.10
            + self.tokens_saida * p["saida"] / 1e6
        )


def responder(historico, contato=None):
    """historico: lista de {role, content}. Devolve Resposta(texto, tools_chamadas)."""
    chamadas = tools.iniciar_registro()

    system = config.SYSTEM
    if contato and memoria.cliente_recorrente(contato):
        system += "\n\nCONTEXTO: este é um cliente recorrente — trate com familiaridade."

    # PROMPT CACHING: o prompt de sistema + as definições de tools são idênticos
    # em toda mensagem. Sem cache você paga por eles a cada chamada; com cache,
    # ~10% do preço a partir da 2ª. O bloco marcado cacheia tools + system juntos
    # (a ordem de renderização é tools -> system -> messages).
    runner = _get_cliente().beta.messages.tool_runner(
        model=config.MODELO,
        max_tokens=config.MAX_TOKENS,
        system=[{
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},
        }],
        tools=tools.TOOLS,
        messages=historico,
    )

    # Guardamos o texto de CADA mensagem do loop, não só da última: em alguns
    # casos a mensagem final vem sem bloco de texto (só tool_use), e entregar
    # string vazia ao cliente é inaceitável em produção.
    textos = []
    entrada = saida = c_escrita = c_leitura = 0
    try:
        for mensagem in runner:
            t = "".join(b.text for b in mensagem.content if b.type == "text").strip()
            if t:
                textos.append(t)
            u = mensagem.usage
            entrada += u.input_tokens
            saida += u.output_tokens
            c_escrita += getattr(u, "cache_creation_input_tokens", 0) or 0
            c_leitura += getattr(u, "cache_read_input_tokens", 0) or 0
    except APIError as e:
        # Rate limit, queda de rede, indisponibilidade: o cliente recebe uma
        # mensagem humana em vez de um crash. O erro fica no log para você.
        logger.exception("falha na API ao responder: %s", e)

    if textos:
        texto = textos[-1]
    else:
        # Falha silenciosa: o loop terminou sem nenhum texto. Registre para você
        # descobrir — senão o cliente recebe o fallback e ninguém fica sabendo.
        logger.warning(
            "resposta sem texto (fallback acionado) | tools=%s | tokens saida=%s",
            chamadas, saida,
        )
        texto = FALLBACK
    return Resposta(
        texto=texto,
        tools_chamadas=list(chamadas),
        tokens_entrada=entrada,
        tokens_saida=saida,
        cache_escrita=c_escrita,
        cache_leitura=c_leitura,
    )


def processar(contato, texto):
    """Entrada única para qualquer canal: salva, responde, salva, devolve texto."""
    memoria.salvar_turno(contato, "user", texto)
    historico = memoria.carregar_historico(contato)
    resp = responder(historico, contato=contato)
    memoria.salvar_turno(contato, "assistant", resp.texto)
    return resp.texto
