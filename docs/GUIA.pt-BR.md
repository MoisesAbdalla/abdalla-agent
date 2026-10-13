# Agente de Vendas — Abdalla Tech

Agente de atendimento/vendas para PC gamer, construído com Claude (tool use).
O **cérebro é independente do canal**: hoje conversa pelo terminal; amanhã, plugar
o WhatsApp é só adicionar um adaptador — sem mexer no agente.

## Estrutura

```
abdalla-agente/
├── agente/            # o CÉREBRO (independente de canal)
│   ├── config.py      # modelo, serviços (fonte da verdade), prompt
│   ├── tools.py       # as "mãos": orçamento, lead, escalar humano
│   ├── memoria.py     # SQLite: histórico, leads, escalações
│   └── core.py        # responder() + processar()  <- ponto de entrada
├── canais/            # os TRANSPORTES
│   ├── base.py        # interface Canal
│   ├── terminal.py    # canal de teste (terminal)
│   └── whatsapp.py    # TEMPLATE p/ plugar o WhatsApp depois
├── evals/             # QUALIDADE (o que torna profissional)
│   ├── casos.py       # casos de teste
│   └── runner.py      # roda: checagem determinística + LLM-como-juiz
└── chat.py            # conversar no terminal
```

## Setup

Esta máquina tem 5 Pythons instalados, então o projeto usa um **venv próprio**
(`.venv/`) — assim nunca importa qual `python` está primeiro no PATH.

O venv já está criado. Se precisar recriar:

```bash
C:\Python314\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

A chave da API fica em variável de ambiente (já configurada):
`ANTHROPIC_API_KEY`.

## Usar

Jeito mais simples — clique duplo, ou pelo terminal:

```bash
.\chat.cmd    # conversar com o agente
```

```bash
.\evals.cmd   # rodar os testes de qualidade
```

```bash
.\painel.cmd  # ver agendamentos, escalações e leads (custo zero)
```

```bash
.\custo.cmd   # medir custo por conversa e projetar gasto mensal
```

## Como descrever seus serviços

Tudo fica em `SERVICOS`, em `agente/config.py`. **Você edita lá e o agente aprende na
hora** — não precisa mexer em mais nada. Preço simples:

```python
"limpeza": {
    "nome": "Limpeza completa de PC", "preco": 150,
    "duracao_h": 2, "prazo": "no mesmo dia",
    "inclui": "gabinete, coolers, fonte, placa-mãe, pasta térmica do processador...",
    "nao_inclui": "revisão interna da placa de vídeo — é o serviço 'revisao_gpu'",
},
```

Quando o mesmo serviço tem faixas de preço, use `variantes` em vez de `preco`:

```python
"revisao_gpu": {
    "nome": "Revisão de placa de vídeo",
    "duracao_h": 2, "prazo": "no mesmo dia",
    "variantes": {
        "low":  {"preco": 150, "quando": "placas de entrada — ex.: GTX 1050, RX 570"},
        "high": {"preco": 250, "quando": "alto desempenho — ex.: RTX 2070+, RX 6700+"},
    },
    "inclui": "pasta térmica do chip, thermal pads, limpeza interna, teste térmico",
},
```

O campo `quando` é o que ensina o agente a classificar a placa do cliente. Se ele não
souber qual variante, a tool o obriga a **perguntar o modelo antes de cotar** — nunca chuta.

Dica: `nao_inclui` vira venda. Ao dizer que a limpeza não cobre a GPU por dentro, o agente
oferece a revisão como complemento — com desconto de combo se levar os dois.

Depois de editar, rode `.\evals.cmd` para confirmar que nada quebrou.

## Autonomia — o que o agente decide sozinho

O agente foi desenhado para **não depender de você** no dia a dia. Alçada em
`agente/config.py`:

| Ele resolve sozinho | Ele chama você |
|---|---|
| Desconto até **10%** (15% em combo) | Desconto acima disso, ou cliente insistindo no impossível |
| **Agendar** o serviço (consulta agenda real e confirma) | Serviço acima de R$ 400 |
| Dúvidas de horário, pagamento, garantia, prazo, local | Reclamação, defeito, problema |
| O que cada serviço **inclui** | Caso realmente fora do padrão |

Você recebe aviso em `dados/avisos.log` a cada lead, agendamento ou escalação.
Para receber no WhatsApp/Telegram/Discord, defina `AVISO_WEBHOOK_URL`.

## Custo (medido, não estimado)

Conversa típica de venda (4 turnos, do "oi" ao lead registrado), `claude-sonnet-5`:

| Otimização | Custo/conversa | 1000 conversas/mês |
|---|---|---|
| Versão inicial | US$ 0,053 | US$ 52,69 |
| + prompt caching | US$ 0,032 | US$ 31,57 |
| + respostas curtas | **US$ 0,022** | **US$ 22,34** |

O que barateou: o prompt de sistema e as tools são idênticos em toda chamada — com
`cache_control` eles custam ~10% a partir da 2ª. E limitar a resposta a 3 linhas
(certo para WhatsApp) cortou os tokens de saída pela metade.

### O que gasta e o que não gasta

| Ação | Gasta? |
|---|---|
| Janela de chat aberta, sem digitar nada | **Não** — o agente só chama a API quando você envia uma mensagem |
| Enviar uma mensagem no chat | Sim, ~US$ 0,005 |
| `.\custo.cmd` | Sim — ele **executa** uma conversa de 4 turnos para medir (~US$ 0,02) |
| `.\evals.cmd` | Sim, o mais caro — 7 casos + juiz (~US$ 0,10) |

Não há nada rodando em background: nenhuma tarefa agendada, nenhum polling.
Toda chamada à API parte de `core.responder()`, que só roda a partir de uma
mensagem sua (chat), de um caso de eval, ou do medidor de custo.

⚠️ Evals custam mais que conversas. Rode com propósito, não em loop.

Direto pelo Python do venv (equivalente):

```bash
.\.venv\Scripts\python.exe chat.py
```

> Não use `python chat.py` — isso pega um Python qualquer do sistema, que não
> tem as dependências instaladas (`ModuleNotFoundError: No module named 'anthropic'`).

## Modelo — decisão baseada em evals, não em achismo

Padrão: **`claude-sonnet-5`**. Medido neste projeto:

| Modelo | Evals | Observação |
|---|---|---|
| `claude-haiku-4-5` | 4/7 | **Não use para atender cliente.** Disse "já registrei seu contato" sem chamar `registrar_lead` — lead perdido e cliente enganado. |
| `claude-sonnet-5` | 7/7 | Confiável em tool use e honestidade. Padrão. |
| `claude-opus-5` | — | Mais caro; use se precisar de negociação mais sofisticada. |

Trocar: `$env:ABDALLA_MODELO = "claude-opus-5"`. Reavalie sempre com `python -m evals.runner`.

## Lições aprendidas (não repita estes erros)

1. **O eval também tem bug.** Critérios de juiz com negativa dupla reprovavam respostas
   corretas. Escreva UMA pergunta positiva e objetiva.
2. **Juiz fraco é pior que juiz nenhum.** Com `haiku` como juiz tivemos falhas fantasma —
   e quase "consertamos" um agente que não estava quebrado. O juiz é `claude-sonnet-5`.
3. **O juiz deve medir risco de negócio, não redação.** "Recusou com as palavras certas?" é
   preferência estética. "Ofereceu algo de graça?" é risco real.
4. **Nunca afrouxe um teste só para ficar verde.** Afrouxe apenas quando souber explicar por
   que ele media a coisa errada — e mantenha a trava determinística.
5. **Falha intermitente existe.** Rode a bateria 2x antes de confiar. Respostas vazias
   apareciam de forma aleatória; por isso `core.py` nunca devolve string vazia.
6. **Catálogo no prompt, preço na tool.** Com o catálogo só na tool, o agente alucinou que
   não fazíamos um serviço que fazemos — e recusou uma venda de R$ 250.

## Plugar o WhatsApp (depois)

O agente não muda. Você:
1. Sobe um provedor (Evolution API self-hosted, Z-API, ou WhatsApp Cloud API).
2. Aponta o webhook dele para um servidor seu (ex.: FastAPI).
3. No webhook, chama `canais.whatsapp.tratar_webhook(payload)`.
4. Preenche `CanalWhatsApp.enviar` com a API de envio do provedor.

Veja `canais/whatsapp.py` — está comentado passo a passo.

## Evoluir

- Novo serviço? Edite `SERVICOS` em `agente/config.py`.
- Achou um erro do agente? Vire um caso em `evals/casos.py` e rode os evals.
- Nova capacidade (agendar, consultar estoque)? Adicione uma tool em `agente/tools.py`.
```
