# Especificação v1 — atende-nutricao (contrato congelado)

> Este arquivo é **protegido** durante a execução longa: o agente implementa contra ele e não o altera.
> Os testes em `tests/` verificam exatamente o que está aqui. Mudança de contrato = humano edita, recongela o hash e reinicia o longrun.

## 0. O que é

Sistema de atendimento ao paciente para **um consultório de nutrição**: agenda de consultas (primeira consulta e retornos, **presencial ou online** com link informado pela equipe), confirmação automática, lista de espera, retorno programado, **plano alimentar** registrado pelo nutricionista e consultado pelo paciente na conversa, **diário** (água, refeições feitas/puladas, peso, foto de refeição) com lembretes opt-in, FAQ, passagem para humano, sinais de alerta, campanhas com trava mínima de publicidade e LGPD de dado de saúde, e exportação de números para o **Painel de Recuperação do Raio-X de Margem** (pacote `clinica`).

Base: o desenho do `atende-clinica` (agenda, confirmação, espera, retorno, FAQ, fila humana, campanhas, LGPD, cadastros, bloqueios, backup, Evolution, Telegram, Docker). O que muda está nas seções 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15, 19 e 20.

Canais: **chat web**, **WhatsApp pela Evolution API** (seção 19) e caixa de saída **simulada** quando a Evolution não está configurada. Equipe interna atende pelo **Telegram** (seção 20) e pela página `/equipe`. Cadastros (seção 16), gestão de agenda (seção 17), backup (seção 18), entrega em **Docker** para VPS (seção 21).

**O bot nunca prescreve** dieta, suplemento, cálculo calórico ou substituição de alimento: ele só mostra o que está no plano daquele paciente e no FAQ. Dúvida fora disso vai para o humano (seção 6).

## 1. Execução

- Ponto de entrada: arquivo executável `./atende` na raiz do repo.
- `./atende serve --porta N --dados DIR [--host H]`
  - `--porta 0` = porta livre escolhida pelo sistema. A **primeira linha** do stdout é `PORTA=<n>` (com flush), impressa quando o servidor já aceita conexões.
  - Escuta em `--host` (padrão `127.0.0.1`; no Docker, `0.0.0.0` passado pelo comando do container — nunca escrito no código).
  - `DIR/nutricao.json` = configuração (seção 2). Se não existir, copiar `exemplos/nutricao.json`.
  - Todo o estado persiste em `DIR/` (ex.: SQLite). **Cria `DIR` se não existir** (no container, `/dados` pode não ter volume montado). Reiniciar com o mesmo `DIR` mantém tudo.
  - O servidor aceita **conexões simultâneas** (os testes disparam 10 pedidos ao mesmo tempo); use servidor com threads e transação no banco.
- **Relógio:** variável de ambiente `ATENDE_AGORA` (`AAAA-MM-DDTHH:MM`, hora local do consultório, sem fuso) fixa o "agora" do processo. Sem ela, usa o relógio real. Datas/horas no contrato são sempre `AAAA-MM-DDTHH:MM` local; datas soltas, `AAAA-MM-DD`; horas soltas, `HH:MM`.
- `./atende raiox --dados DIR --mes AAAA-MM --acompanhamento ARQ` (seção 12).
- `./atende backup` / `./atende restaurar` (seção 18).
- Integrações externas **só** por variáveis de ambiente (seções 19–20). Sem elas, nenhuma chamada de rede sai do processo. Nenhuma URL externa, chave ou token escrito no código. O sistema **nunca baixa mídia** recebida pelo webhook (seção 19).

## 2. `nutricao.json`

```json
{
  "nome": "Nutri Bem",
  "token": "segredo",                 // exigido no header X-Token das rotas da equipe [E]
  "passo_min": 30,                    // grade de horários
  "antecedencia_min_horas": 2,        // não oferece/aceita horário antes de agora + isto
  "janela_dias": 14,                  // até quantos dias à frente o chat oferece horários
  "confirmacao_horas": 48,            // pede confirmação quando a consulta começa em até 48 h
  "retorno_aviso_dias": 7,            // avisa o retorno quando faltam até 7 dias
  "lembrete_tolerancia_min": 60,      // lembrete de água/refeição só sai até X min depois do horário
  "atende_online": true,              // false = toda consulta é presencial (o chat não pergunta)
  "feriados": ["2026-10-12"],
  "horarios": { "seg": [["08:00","12:00"],["14:00","18:00"]], "ter": [...], "qua": [...], "qui": [...], "sex": [...], "sab": [["08:00","12:00"]], "dom": [] },
  "profissionais": [ { "id": "lia", "nome": "Dra. Lia", "servicos": ["primeira","retorno"] } ],
  "servicos": [ { "id": "primeira", "nome": "Primeira consulta", "duracao_min": 60, "retorno_dias": 30 } ],
  "faq": [ { "id": "convenios", "perguntas": ["vocês aceitam convênio"], "resposta": "Atendemos Unimed e particular." } ]
}
```

`retorno_dias` pode ser `null` (sem retorno). Dias da semana: `seg ter qua qui sex sab dom`. Não há campo de conselho: o consultório é de nutrição (CFN) e a trava de campanha é a da seção 11. A fixture dos testes está em `tests/fixtures/nutricao.json`; `exemplos/nutricao.json` é igual, com token `TROQUE-ESTE-TOKEN`.

## 3. Regras de agenda

- Horário candidato: começa no início de uma janela e anda de `passo_min` em `passo_min`; vale se `[inicio, inicio+duracao)` cabe inteiro na janela (`inicio + duracao <= fim da janela`).
- **Inválido (422)** se: não é horário candidato (fora da grade ou não cabe na janela); dia em `feriados`; `inicio < agora + antecedencia_min_horas`; profissional não faz o serviço ou está inativo; há bloqueio do profissional sobrepondo `[inicio, fim)` (seção 17); `modalidade` fora de `presencial`/`online`; `modalidade: "online"` com `atende_online: false`.
- **Ocupado (409)** se é válido mas sobrepõe outro agendamento **ativo** do mesmo profissional (ou, sem profissional indicado, de todos que fazem o serviço). Intervalos semiabertos: sobrepõe se `inicio < outro.fim` e `fim > outro.inicio`.
- `GET /api/horarios` lista só horários válidos e livres (sem exigir antecedência maior do que a regra acima).
- Agendamento ativo = status `agendado`, `confirmado`, `realizado` ou `falta`. `cancelado` libera o horário.
- **Modalidade:** `presencial` (padrão) ou `online`. Consulta online tem `link` (`null` até a equipe informar, seção 5). Remarcar mantém `modalidade` e `link`.
- Dois pedidos simultâneos para o mesmo horário/profissional: exatamente um vence (201), o outro recebe 409.

## 4. Autenticação

Rotas marcadas **[E]** (equipe) exigem header `X-Token` igual a `nutricao.json.token`; sem ele ou errado → **401**, e essa checagem vem **antes** de qualquer outra (corpo vazio ou inválido sem token → 401, não 422/404). Rotas públicas: `/`, `/equipe` (página; os dados vêm de rotas [E]), `/api/saude`, `GET /api/servicos`, `/api/horarios`, `/api/mensagens`. Webhooks têm segredo próprio (seções 19 e 20).

## 5. API HTTP (JSON, UTF-8)

Toda resposta com corpo JSON (2xx e erros) sai com header `Content-Type: application/json` (os testes só decodificam JSON quando o header diz `json`); `204` sem corpo.

| Método e rota | Corpo | Resposta |
|---|---|---|
| `GET /api/saude` | — | 200 `{"ok": true, "versao": "<conteúdo de VERSION>"}` |
| `GET /api/servicos` | — | 200 `{"servicos": [{id, nome, duracao_min}]}` só os ativos, na ordem do JSON e depois ordem de criação |
| `GET /api/horarios?servico=S&data=AAAA-MM-DD[&profissional=P]` | — | 200 `{"horarios": [{"inicio", "profissional"}]}` ordenado por `inicio`, depois `profissional`; serviço inexistente → 404; profissional inexistente → 404 |
| `POST /api/pacientes` [E] | `{nome, telefone, consentimento_marketing?: bool, email?, nascimento?: "AAAA-MM-DD"}` | 201 `{id}`; telefone já cadastrado → 200 com o mesmo `{id}` (demais campos não mudam); telefone inválido → 400 |
| `GET /api/pacientes?busca=T` [E] | — | 200 `{"pacientes": [{id, nome, telefone, email, nascimento, consentimento_marketing, nao_contatar}]}`; `busca` casa parte do nome (sem acento, sem caixa) ou dígitos do telefone; sem `busca` = todos, ordem de criação |
| `PUT /api/pacientes/{id}` [E] | `{nome?, telefone?, email?, nascimento?, consentimento_marketing?, nao_contatar?}` | 200 com o paciente; telefone inválido → 400; telefone de outro paciente → 409 |
| `GET /api/pacientes/{id}/dados` [E] | — | 200 `{paciente, agendamentos, mensagens, planos, diario, pesos, metas}` (seção 13) |
| `DELETE /api/pacientes/{id}` [E] | — | 204; anonimiza e apaga o dado de saúde (seção 13). O registro continua existindo com o mesmo `id`: `GET .../dados` depois disso devolve 200 |
| `POST /api/agendamentos` [E] | `{paciente_id, servico, inicio, profissional?, modalidade?}` | 201 `{id, status: "agendado", inicio, fim, profissional, modalidade, link: null}`; sem `profissional` = o primeiro livre por ordem de cadastro dos profissionais; horário ocupado → 409; inválido (seção 3) → 422; paciente/serviço/profissional inexistente → 404 |
| `GET /api/agendamentos?data=AAAA-MM-DD` [E] | — | 200 `{"agendamentos": [{id, paciente_id, nome, telefone, servico, profissional, inicio, fim, status, modalidade, link}]}` ordenado por `inicio`, depois `id`; inclui cancelados (filtrar pelo `status`) |
| `GET /api/agendamentos?de=AAAA-MM-DD&ate=AAAA-MM-DD[&profissional=P]` [E] | — | mesma lista, pontas inclusivas |
| `POST /api/agendamentos/{id}/cancelar` [E] | — | 200 `{status: "cancelado"}`; dispara a lista de espera (seção 7); já cancelado → 409 |
| `POST /api/agendamentos/{id}/remarcar` [E] | `{inicio}` | 200 com o agendamento no novo horário (mesmo `id`, status `agendado`, a confirmação volta a ser devida); mesmas regras de 409/422 (o próprio agendamento não conta como ocupação) |
| `POST /api/agendamentos/{id}/presenca` [E] | `{compareceu: bool}` | 200 `{status: "realizado" \| "falta"}`; `realizado` + `retorno_dias` cria retorno (seção 8); pode ser marcada a qualquer momento (não depende do relógio) |
| `POST /api/agendamentos/{id}/link` [E] | `{link}` | 200 `{id, link}`; `modalidade` presencial → 422; `link` vazio → 422. O link entra na confirmação (seção 8) e na resposta `link` do chat (seção 6) |
| `POST /api/espera` [E] | `{paciente_id, servico, data}` | 201 `{id}` |
| `POST /api/tarefas/rodar` [E] | `{agora?}` (padrão = relógio do processo; o valor vale **só para esta rodada**) | 200 `{"enviadas": n, "reenviadas": n}` (seções 8 e 19); idempotente: rodar de novo no mesmo instante → `enviadas: 0` |
| `GET /api/saida` [E] | — | 200 `{"mensagens": [{id, tipo, telefone, paciente_id, texto, agendamento_id, status, quando}]}` em ordem de criação. `tipo` ∈ `confirmacao, espera, retorno, lembrete, plano, campanha, humano`; `agendamento_id` só em `confirmacao` (senão `null`); `status` ∈ `simulado, enviado, pendente` (seção 19); `quando` = o "agora" vigente na criação, `AAAA-MM-DDTHH:MM` (numa rodada `tarefas/rodar {agora}`, esse `agora`) |
| `POST /api/mensagens` | `{telefone, texto}` | 200 `{"respostas": [texto, ...]}` (seção 6) |
| `GET /api/atendimento-humano` [E] | — | 200 `{"fila": [{id, telefone, nome, motivo, prioridade, status}]}` só os `aberto`, ordem de abertura; `prioridade` ∈ `normal, alta`; `motivo` ∈ `atendente, nao_entendi, emergencia, alerta, duvida_plano` |
| `POST /api/atendimento-humano/{id}/responder` [E] / `.../encerrar` [E] | `{texto}` / — | 200 (seção 20) |
| `POST /api/campanhas` [E] | `{texto}` | 200 `{"enviadas": n}` ou 422 `{"violacoes": [codigos]}` (seção 11); `texto` ausente, vazio ou só espaços → 422 |
| `GET /api/raiox?mes=AAAA-MM` [E] | — | 200 (seção 12) |

Plano alimentar: seção 9. Diário, metas e peso: seção 10. Cadastros (profissionais, serviços, FAQ): seção 16. Bloqueios: seção 17.

**Ids inexistentes:** qualquer rota com `{id}` no caminho e qualquer referência por id no corpo (`paciente_id`, `servico`, `profissional`) a algo que não existe → **404**, antes das validações de 409/422. Corpo que não é JSON ou sem os campos obrigatórios → **422**.

**Telefone:** aceita com ou sem `+55`, espaços, parênteses e hífen; conta os dígitos: 10 ou 11 dígitos (DDD + 8 ou 9) sem o país, ou 12/13 começando por `55`; normaliza para `+55DDNNNNNNNNN`. Fora disso → inválido. Todas as respostas usam o telefone normalizado.

**Rotas síncronas:** `POST /api/mensagens`, `tarefas/rodar`, `campanhas`, `agendamentos/{id}/cancelar` (oferta da lista de espera), `pacientes/{id}/plano/enviar` e `atendimento-humano/{id}/responder` só devolvem a resposta HTTP depois de criar as mensagens de saída e tentar os envios (o `status` em `/api/saida` já está definido). Respostas ao webhook da Evolution e avisos ao Telegram podem ser assíncronos.

## 6. Conversa (`POST /api/mensagens`)

**Normalização:** minúsculas, sem acento, sem pontuação — **exceto `,` e `.` entre dois dígitos**, que são preservados (`82,5` continua `82,5`). *Token* = palavra inteira do texto normalizado (separado por espaço). "Contém `x`" = substring do texto normalizado; "contém o token `x`" = palavra inteira. *Número* = primeiro trecho `\d+([.,]\d+)?` do texto normalizado.

Ordem de decisão (a primeira regra que casa responde; cada regra diz se agenda ou registra algo):

1. **Emergência física** — contém um destes: `dor no peito`, `falta de ar`, `desmaio`, `desmaiei`, `desmaiou`, `convulsao`, `sangramento`, `sangrando`, `infarto`, `avc`, `nao paro de vomitar`, `vomitando sem parar`, `vomito sem parar`, `hipoglicemia`, `suor frio`, `visao turva`, `tremedeira`. Resposta contém `192` e `pronto-socorro`; entra na fila humana com `prioridade: "alta"`, `motivo: "emergencia"`. Não agenda nem registra nada.
2. **Alerta comportamental** — contém um destes: `me matar`, `suicidio`, `me machucar`, `me cortar`, `compulsao`, `vomitei de proposito`, `forcei o vomito`, `provoquei o vomito`, `laxante`, `parei de comer`, `nao como ha dias`, `sem comer ha dias`, `jejum de dias`. Resposta contém `188` (CVV) e `nutricionista`; fila humana `prioridade: "alta"`, `motivo: "alerta"`. Não agenda nem registra nada. As regras 1 e 2 respondem **mesmo com atendimento humano aberto** (seção 20).
3. **Parar** — texto igual a `parar`, `sair` ou `pare`: paciente fica `nao_contatar`; resposta contém `não vai mais receber`. As mensagens automáticas (`confirmacao`, `espera`, `retorno`, `lembrete`, `campanha`) **não são criadas** para esse telefone; `plano/enviar` recusa com 409 (seção 9); respostas da equipe (`humano`) continuam. Telefone sem paciente cadastrado: a preferência fica guardada pelo telefone e se aplica ao paciente quando ele for criado (pela API ou pelo chat).
4. **Parar lembretes** — texto igual a `parar lembretes`: `lembretes_agua` vira `[]` e `lembretes_refeicoes` vira `false` (seção 10); `nao_contatar` **não** muda; resposta contém `lembretes`.
5. **Humano** — contém `atendente`, `humano` ou `falar com alguem`: fila humana `normal`, `motivo: "atendente"`; resposta contém `atendente`.
6. **Fluxo em andamento** (agendamento pelo chat, abaixo) consome a mensagem.
7. **Resposta a pendência:** se a última mensagem da **caixa de saída** (`/api/saida`; respostas do bot na conversa não contam) para o telefone foi `confirmacao` (sem resposta ainda): texto **igual a** `1`, `sim` ou `confirmo` → status `confirmado`, resposta contém `confirmad`; texto **igual a** `2`, `cancelar` ou `nao` → status `cancelado` (dispara espera), resposta contém `cancelad`. Se foi `espera` (sem resposta): texto igual a `1` ou `sim` → agenda o horário ofertado se ainda livre (resposta contém `agendad`), senão resposta contém `ocupado`. Qualquer outro texto **não consome** a pendência (ex.: `nao comi` e `1 copo` seguem para a regra 8).
8. **Registro no diário** (seção 10), nesta ordem:
   - **Peso:** contém o token `kg`, `quilo`, `quilos`, `peso`, `pesei` ou `pesando` **e** um número → registra o peso (regras de faixa, arredondamento e resposta na seção 10). Com o token `peso` e **sem** número → resposta contém o último peso registrado (o de maior `quando`; empate → maior `id`; vale o registrado pela equipe também) no formato `<v> kg` ou `nenhum peso`.
   - **Água:** contém o token `copo` ou `copos` → registra copos de água (quantidade = primeiro inteiro do texto; sem inteiro = 1).
   - **Refeição:** contém `pulei`, `pulou`, `nao comi`, `nao fiz` ou `nao tomei` → `pulada`; senão contém o token `comi`, `fiz`, `tomei`, `feita`, `feito`, `almocei` ou `jantei` → `feita`. Sem plano ativo: resposta contém `nutricionista` e nada é registrado.
9. **Plano alimentar** — contém `meu plano`, `plano alimentar`, `cardapio`, `dieta`, `posso comer`, `pode comer`, `o que comer` ou `o que como`:
   - sem plano ativo (inclusive telefone sem paciente) → resposta contém `nutricionista` (e nada mais acontece);
   - casa uma **refeição** (regra de casamento na seção 9) → responde **só a linha daquela refeição** (os nomes das outras refeições não aparecem na resposta);
   - não casa refeição e contém `posso comer`, `pode comer`, `o que comer` ou `o que como` (ex.: `posso comer chocolate?`) → dúvida fora do plano: resposta contém `plano`, `nutricionista` e `atendente`; entra na fila humana `normal`, `motivo: "duvida_plano"`;
   - senão (`meu plano`, `plano alimentar`, `cardapio`, `dieta`) → responde o plano inteiro (formato na seção 9).
10. **Link** — contém o token `link`: próximo agendamento `online` com status `agendado`/`confirmado` e `inicio >= agora` do telefone (menor `inicio`): com `link` → resposta contém o link; sem `link` → resposta contém `equipe`; não há consulta online → resposta contém `não encontrei`.
11. **Agendar** — contém `agendar`, `marcar` ou `consulta`: inicia o fluxo.
12. **FAQ** — palavras significativas (≥ 3 letras, fora de artigos/preposições/pronomes comuns) de alguma pergunta do FAQ: se ≥ 60 % delas aparecem no texto, responde **exatamente** a `resposta` daquele item (só ela, uma mensagem). Mais de um item casa → o de maior %; empate → o primeiro do FAQ.
13. **Não entendi** — resposta contém `não entendi` e oferece `atendente`. Na **segunda** seguida sem entender, entra na fila humana (`normal`, `motivo: "nao_entendi"`) automaticamente.

**Fluxo de agendamento pelo chat** (estado por telefone, persistido; em cada passo a resposta faz a pergunta do passo):
- telefone sem paciente → pergunta o nome (resposta contém `nome`); a próxima mensagem vira o nome e o paciente é criado (`consentimento_marketing: false`). Telefone com paciente pula este passo;
- lista os serviços ativos numerados `1 - <nome>` na ordem da seção 5;
- escolhido o número, oferece os **3 primeiros** horários livres a partir de `agora + antecedencia_min_horas`, dentro de `janela_dias`, em todos os profissionais ativos, ordem da seção 5; cada linha `N) DD/MM HH:MM com <nome do profissional>`;
- escolhido o número: com `atende_online: true`, pergunta a modalidade — resposta contém `1 - Presencial` e `2 - Online`; `1` = presencial, `2` = online. Com `atende_online: false`, não pergunta (presencial);
- cria o agendamento; resposta contém `agendad`, `DD/MM` e `HH:MM`; se online, contém também `online`. Se o horário escolhido foi ocupado nesse meio-tempo, resposta contém `ocupado` e oferece de novo os 3 primeiros.
- número inválido em qualquer passo → repete as opções do passo. `cancelar` dentro do fluxo → sai do fluxo (resposta contém `cancelad` e nada é agendado).
- O bot **nunca** inventa preço, diagnóstico, dieta, suplemento ou cálculo: fora do plano e do FAQ cai nas regras 9 (fila humana) ou 13.

## 7. Lista de espera

Ao cancelar (pela API ou pela conversa), o primeiro pedido de espera ainda não atendido com o mesmo `servico` e a mesma `data` do horário liberado (ordem de criação), cujo paciente não esteja `nao_contatar`, recebe mensagem `tipo: "espera"` contendo `HH:MM` do horário e `1`. O pedido fica `ofertado` (não recebe outra oferta do mesmo horário). Não há oferta se nenhum pedido serve.

## 8. Confirmação, retorno e lembretes (`POST /api/tarefas/rodar`)

- **Confirmação:** todo agendamento `agendado` com `agora < inicio <= agora + confirmacao_horas` que ainda não recebeu confirmação (desde a última criação/remarcação) → mensagem `tipo: "confirmacao"` com `agendamento_id`. Texto contém o nome do serviço, `DD/MM`, `HH:MM`, `1` (confirmar) e `2` (cancelar). **Não contém valor em R$.** Consulta `online`: o texto contém `online` e, se houver `link`, o link; sem link, contém a palavra `link` (a equipe vai mandar). Consulta presencial: o texto **não** contém `online`.
- **Retorno:** presença `realizado` de serviço com `retorno_dias` cria um retorno com `data = data do atendimento + retorno_dias` e guarda a data do atendimento de origem. Quando `agora >= data − retorno_aviso_dias` e ainda não avisado → mensagem `tipo: "retorno"` com o nome do serviço. Uma vez só.
- **Lembretes** (seção 10): para cada paciente com telefone, não `nao_contatar`:
  - para cada `H` em `lembretes_agua`: com `T = data(agora) + H`, se `T <= agora <= T + lembrete_tolerancia_min` e ainda não houve lembrete de água para (paciente, `data(agora)`, `H`) → mensagem `tipo: "lembrete"` cujo texto contém `água`. Fora da janela de tolerância o lembrete daquele dia **não sai nunca** (não acumula);
  - com `lembretes_refeicoes: true` e plano ativo: para cada refeição do plano com horário `H`, mesma janela e mesma unicidade por (paciente, dia, refeição) → `tipo: "lembrete"` cujo texto contém o nome da refeição e suas opções.
- `enviadas` = mensagens criadas nesta rodada (mesmo que o envio pela Evolution fique `pendente`); `reenviadas` = `pendente` que viraram `enviado` (seção 19). Paciente `nao_contatar` nunca recebe (a mensagem **não é criada**). Confirmação, retorno e lembrete **não** dependem de `consentimento_marketing` (LGPD art. 11, II, f — tutela da saúde, pedidos do próprio paciente); campanha depende (seção 11).

## 9. Plano alimentar

Texto estruturado, escrito pelo nutricionista; **sem cálculo nutricional** no v1 (nem calorias, nem macros — ficam para o nutricionista).

| Método e rota | Corpo | Resposta |
|---|---|---|
| `POST /api/pacientes/{id}/plano` [E] | `{refeicoes: [{horario: "HH:MM", nome, opcoes: [texto, ...], observacoes?}], observacoes?}` | 201 `{id, versao}`; `versao` = 1 + nº de planos anteriores do paciente; o novo plano vira o **ativo**. 422 se `refeicoes` ausente/vazio, `horario` fora de `HH:MM`, `nome` vazio ou `opcoes` vazio; paciente inexistente → 404 |
| `GET /api/pacientes/{id}/plano` [E] | — | 200 `{id, versao, refeicoes: [{horario, nome, opcoes, observacoes}], observacoes, criado_em, enviado_em}` (o ativo); `refeicoes` **ordenadas por `horario`** (empate: ordem enviada); `observacoes` ausente (do plano ou de uma refeição) = `""`; `enviado_em` = `null` até o envio; sem plano → 404 |
| `GET /api/pacientes/{id}/planos` [E] | — | 200 `{"planos": [{id, versao, criado_em, enviado_em}]}` em ordem crescente de `versao` |
| `POST /api/pacientes/{id}/plano/enviar` [E] | — | 200 `{"enviadas": 1}`: cria mensagem `tipo: "plano"` com o texto do plano (abaixo) e grava `enviado_em = agora`; sem plano → 404; paciente `nao_contatar` → 409 `{"erro": "nao_contatar"}` |

**Texto do plano** (o mesmo na mensagem `plano` e na resposta do chat):

```
Seu plano alimentar (versão <versao>, de DD/MM/AAAA):
<HH:MM> <nome>: <opção 1> / <opção 2> / ...[ — <observações da refeição>]
...
[<observações gerais>]
```

Uma linha por refeição, na ordem de `horario`; as opções separadas por ` / `; o sufixo ` — <observações>` só quando há observação; a última linha é `observacoes` do plano, quando não vazia. `DD/MM/AAAA` = data de `criado_em`.

**Casamento de refeição** (regra 9 da seção 6): palavras significativas do `nome` de cada refeição (≥ 3 letras, fora de artigos/preposições — `da`, `de`, `do`, `das`, `dos`, `com`, `para`, `pre`, `pos` não contam); a refeição que tem **mais** palavras presentes como tokens do texto vence (precisa de ao menos uma); empate → a de menor `horario`. Ex.: com `Café da manhã (07:30)`, `Lanche da manhã (10:00)`, `Almoço (12:30)`, `Lanche da tarde (16:00)`, `Jantar (20:00)`: `o que posso comer no lanche da tarde` → `Lanche da tarde` (2 palavras); `o que como no lanche` → `Lanche da manhã` (empate, menor horário); `posso comer chocolate` → nenhuma → dúvida fora do plano.

Linha de uma refeição na resposta: `<HH:MM> <nome>: <opções>[ — <observações>]` (igual à do texto do plano).

## 10. Diário, metas e peso

Todo registro tem `quando` = relógio do processo no momento (`AAAA-MM-DDTHH:MM`). *Dia* de um registro = `data(quando)`.

| Método e rota | Corpo | Resposta |
|---|---|---|
| `GET /api/pacientes/{id}/diario[?de=AAAA-MM-DD&ate=AAAA-MM-DD]` [E] | — | 200 `{"registros": [{id, tipo, quando, valor, refeicao, status, mimetype, caption, message_id, origem}], "resumo": {agua_copos, refeicoes_feitas, refeicoes_puladas, adesao_pct, fotos}}`; `tipo` ∈ `agua, refeicao, peso, foto`; campos que não se aplicam = `null`; ordem por `quando`, depois `id`; filtro por dia, pontas inclusivas; sem filtro = tudo. `resumo` sobre os registros filtrados: `agua_copos` = soma de `valor` dos `agua`; `refeicoes_feitas`/`refeicoes_puladas` = contagens; `adesao_pct` = `feitas ÷ (feitas + puladas) × 100` com 1 casa (0 se não houver); `fotos` = contagem |
| `GET /api/pacientes/{id}/pesos` [E] | — | 200 `{"pesos": [{id, quando, peso, origem}], "variacao": <último − primeiro, 1 casa> ou null se houver menos de 2}`; ordem por `quando`, depois `id`; `origem` ∈ `chat, equipe` |
| `POST /api/pacientes/{id}/pesos` [E] | `{peso, quando?}` | 201 `{id}` com `origem: "equipe"`; `peso` fora de `[20, 400]` ou não numérico → 422; `quando` fora do formato → 422; padrão `quando` = agora |
| `GET /api/pacientes/{id}/metas` [E] | — | 200 `{lembretes_agua: ["HH:MM", ...], lembretes_refeicoes: bool, meta_agua_copos: int \| null}`; padrão `[]`, `false`, `null` |
| `PUT /api/pacientes/{id}/metas` [E] | qualquer subconjunto dos três campos | 200 com os três campos; campo omitido não muda; horário fora de `HH:MM` ou `meta_agua_copos` não inteiro positivo (ou `null`) → 422 |

**Peso pela conversa** (regra 8): valor = número com `,` ou `.` como separador, arredondado a **1 casa (meio para cima)**. Faixa aceita `20 <= peso <= 400`; fora dela a resposta contém `entre 20 e 400` e nada é registrado. Registro `{tipo: "peso", valor, origem: "chat"}`. A resposta é **neutra**: contém `registrad` e o valor no formato `<inteiro>,<decimal> kg` (ex.: `82,5 kg`; `82 kg` vira `82,0 kg`) e **não contém** nenhum destes trechos: `parabens`, `otimo`, `muito bem`, `que pena`, `cuidado`, `engordou`, `emagreceu`, `ganhou`, `perdeu`, `ruim` (texto normalizado). O sistema **nunca comenta** a evolução do peso com o paciente; a série é para o nutricionista.

**Água pela conversa:** registro `{tipo: "agua", valor: n}`; resposta contém `registrad` e o total do dia: `<total> de <meta> copos` quando `meta_agua_copos` está definida, senão `<total> copo` (`1 copo`, `3 copos`).

**Refeição pela conversa:** exige plano ativo. A refeição é a que **casa pelo nome** (regra da seção 9); se nenhuma casa, a refeição do plano com **maior `horario <= hora(agora)`**, ou a primeira do plano se não houver. Registro `{tipo: "refeicao", refeicao: <nome>, status: "feita" | "pulada"}`; resposta contém `registrad` e o nome da refeição.

**Foto de refeição** (seção 19): registro `{tipo: "foto", mimetype, caption, message_id, origem: "whatsapp"}` só com metadados (`message_id` = `key.id` da Evolution, a referência para achar a imagem no próprio WhatsApp); a mídia **não é baixada nem guardada**.

Telefone **sem paciente** cadastrado: peso, água, refeição e foto não são registrados; a resposta contém `cadastro` (o paciente precisa estar cadastrado pela equipe ou ter agendado pelo chat).

## 11. Campanhas e trava de publicidade

`POST /api/campanhas {texto}` cria `tipo: "campanha"` só para pacientes com `consentimento_marketing: true`, sem `nao_contatar` e com telefone (LGPD art. 11, I — consentimento específico para dado de saúde). Antes de enviar, valida o texto em minúsculas e sem acento (**pontuação mantida**, para `100%`). O `422` lista **todos** os códigos violados; qualquer violação → 422 e nada é enviado.

| Código | Detecta |
|---|---|
| `promessa_resultado` | `garantido`, `garantia de resultado`, `resultado garantido`, `garantimos`, `100%` |
| `antes_depois` | `antes e depois` |

⚠ **Mínimo comum seguro**, não a regra do CFN: o Raio-X (`docs/setores/servicos-pesquisa-2026-10.md`) não pesquisou o Conselho Federal de Nutricionistas; os dois códigos acima vêm do que CFM, CFO e COFFITO proíbem em comum (promessa de resultado e antes-e-depois). **O dono confirma as regras do CFN antes de publicar campanha** (`docs/DECISOES-ABERTAS.md`). Nenhum artigo de resolução do CFN é citado aqui de propósito.

## 12. Exportação para o Raio-X (Painel de Recuperação)

`GET /api/raiox?mes=AAAA-MM` → `{"pacote": "clinica", "mes": "AAAA-MM", "valores": {...}}`, com números arredondados a 1 casa (meio para cima):

- `atendimentos_mes` = agendamentos `realizado` com `inicio` no mês (inteiro);
- `falta_pct` = `falta ÷ (realizado + falta) × 100` no mês (0 se não houver);
- `ocupacao_pct` = minutos de agendamentos ativos no mês ÷ minutos disponíveis no mês (todas as janelas de todos os profissionais ativos, menos feriados; horário próprio do profissional quando houver) × 100;
- `clientes_novos_mes` = pacientes cujo **primeiro** `realizado` cai no mês;
- `retorno_atual_pct` = dos retornos (seção 8) com `data` no mês, % cujo paciente tem **outro** agendamento `realizado` (qualquer serviço, diferente do que gerou o retorno) com `data(inicio)` em `(data_origem, data + 30 dias]` — isto é, depois do atendimento de origem e até 30 dias depois da data prevista (0 se não houver retornos).

Só esses cinco ids vão em `valores` (são entradas do pacote `clinica` do Raio-X). `./atende raiox --dados DIR --mes M --acompanhamento ARQ`: lê `ARQ` (formato do `raio-x-margem/app/painel-motor.js`: `{tipo: "acompanhamento", pacote, cliente, base: {data, valores}, meses: [{mes, valores, obs}]}`), insere ou substitui o mês `M` com `valores` = os da rota acima **mesclados** sobre os valores do mês anterior (ou da base, se não houver mês anterior) e `obs: "atende-nutricao"`, e grava de volta. Campos que o sistema não mede (ex.: `ticket_medio`, `glosa_pct`) ficam como estavam. Sai com código 0.

## 13. LGPD (dado de saúde = sensível, art. 11)

- `GET /api/pacientes/{id}/dados` devolve tudo o que há do paciente: `paciente` `{id, nome, telefone, email, nascimento, consentimento_marketing, nao_contatar}`, `agendamentos` (mesmo formato da listagem), `mensagens` = recebidas e enviadas, cada uma `{direcao: "entrada" | "saida", texto, quando}`, `planos` = todos os planos com refeições (ordem de versão), `diario` = registros (formato da seção 10), `pesos` (formato da seção 10) e `metas` (formato da seção 10).
- `DELETE /api/pacientes/{id}`: nome vira `removido`, telefone vira `null`, `email`/`nascimento` viram `null`, agendamentos `agendado`/`confirmado` viram `cancelado` (os `realizado`/`falta` ficam), textos de mensagens dele viram `""`, **planos, diário e pesos são apagados** (listas vazias em `/dados`) e `metas` volta ao padrão. Depois disso, mensagens ao telefone antigo são tratadas como de telefone desconhecido. Números agregados do `/api/raiox` continuam contando os atendimentos passados.

## 14. Fora do v1 (não implementar; portão humano ou próxima versão)

Cálculo nutricional automático (calorias, macros, substituições), análise de imagem da foto de refeição (só metadados no v1), download/armazenamento de mídia, WhatsApp Cloud API oficial da Meta (v1 usa a Evolution), SMS/e-mail, deploy na VPS (é do humano: README explica), cobrança/sinal por Pix e planos/assinatura (PSP), prontuário e anamnese, convênio/glosa/TISS, vários consultórios no mesmo servidor, login por usuário, LLM nas respostas (pode entrar depois atrás de uma opção desligada por padrão; os testes nunca a usam), videochamada própria (o link é de ferramenta externa, informado pela equipe), interface EN/ES.

## 15. Páginas

- `GET /` → HTML do chat do paciente, com elemento `id="chat"`, que usa `/api/mensagens`.
- `GET /equipe` → HTML da equipe com elementos `id="agenda"`, `id="fila-humano"`, `id="saida"`, `id="pacientes"`, `id="plano"`, `id="diario"`, `id="pesos"` e `id="faq"`; pede o token e usa as rotas [E] (agenda, pacientes, plano alimentar por paciente, diário/adesão e série de peso por paciente, FAQ, fila humana com responder/encerrar). Sem dependência de CDN.

## 16. Cadastros [E]

`nutricao.json` é lido a cada início para `nome, token, passo_min, antecedencia_min_horas, janela_dias, confirmacao_horas, retorno_aviso_dias, lembrete_tolerancia_min, atende_online, feriados, horarios`. Já `profissionais`, `servicos` e `faq` só **semeiam** o banco na primeira vez (banco vazio); depois o banco é a fonte e se edita pela API.

| Método e rota | Corpo | Resposta |
|---|---|---|
| `GET /api/profissionais` | — | 200 `{"profissionais": [{id, nome, servicos, registro, horarios, ativo}]}` ordem de cadastro (`registro` = CRN, pode ser `null`; `horarios` = `null` quando usa o do consultório) |
| `POST /api/profissionais` | `{id, nome, servicos, registro?, horarios?}` | 201; `id` repetido → 409; serviço inexistente → 422 |
| `PUT /api/profissionais/{id}` | campos parciais | 200 com o registro atualizado; inexistente → 404 |
| `DELETE /api/profissionais/{id}` | — | 200 `{"ativo": false}`. Inativo some de `/api/horarios`, do chat e não aceita agendamento novo (422); os agendamentos já feitos continuam |
| `GET /api/servicos` (público) | — | só os ativos |
| `POST /api/servicos` | `{id, nome, duracao_min, retorno_dias?}` | 201; `id` repetido → 409 |
| `PUT /api/servicos/{id}` / `DELETE /api/servicos/{id}` | parcial / — | 200 / 200 `{"ativo": false}` (some da lista pública e do chat) |
| `GET /api/faq` | — | 200 `{"faq": [{id, perguntas, resposta}]}` ordem de cadastro |
| `POST /api/faq` | `{perguntas: [..], resposta}` | 201 `{id}`; o bot passa a usar na hora |
| `DELETE /api/faq/{id}` | — | 204; o bot para de usar na hora |

## 17. Gestão de agenda [E]

- **Horário por profissional:** `horarios` do profissional (mesmo formato do consultório) substitui o do consultório só para ele. `null` = o do consultório.
- **Bloqueios** (férias, folga, congresso): `POST /api/bloqueios {profissional, inicio, fim, motivo}` → 201 `{id, conflitos: [ids de agendamentos ativos que caem no bloqueio]}` (não cancela nada sozinho). Horários que sobrepõem `[inicio, fim)` somem de `/api/horarios` e o agendamento neles dá 422. `GET /api/bloqueios?profissional=P` → 200 `{"bloqueios": [{id, profissional, inicio, fim, motivo}]}` ordem por `inicio`, depois `id`. `DELETE /api/bloqueios/{id}` → 204 e libera.
- **Listagem por período:** `GET /api/agendamentos?de=AAAA-MM-DD&ate=AAAA-MM-DD[&profissional=P]` (inclusivo nas duas pontas), ordenado por `inicio`, depois `id`; continua valendo `?data=`.

## 18. Banco de dados

- `./atende backup --dados DIR --saida ARQ` → grava em `ARQ` uma cópia consistente de todo o estado (pode rodar com o servidor ligado). Código 0.
- `./atende restaurar --dados DIR --entrada ARQ` → com o servidor parado, substitui o estado de `DIR` pelo do backup. Código 0. Ao subir de novo, tudo volta como estava no momento do backup.

## 19. WhatsApp pela Evolution API

Variáveis: `EVOLUTION_URL` (ex.: `http://evolution:8080` — este exemplo fica **só nesta spec e no README**: no código e no `.env.exemplo` nenhuma URL além de `127.0.0.1`/`localhost`, senão o `verificar-limites.sh` e o teste do `.env.exemplo` acusam), `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCIA`, `WEBHOOK_SEGREDO`. Sem `EVOLUTION_URL` → canal simulado (só caixa de saída, `status: "simulado"`).

**Entrada** — `POST /webhook/evolution/{WEBHOOK_SEGREDO}` (segredo errado → 404). Formato da Evolution v2:
```json
{"event": "messages.upsert", "instance": "nutricao",
 "data": {"key": {"remoteJid": "5541999990001@s.whatsapp.net", "fromMe": false, "id": "ABC123"},
          "pushName": "Maria", "message": {"conversation": "oi"}, "messageType": "conversation"}}
```
- Sempre responde 200. Ignora: `event` diferente de `messages.upsert`, `fromMe: true`, `remoteJid` de grupo (`@g.us`), `key.id` já processado (a Evolution reenvia).
- Texto = `message.conversation` ou `message.extendedTextMessage.text`. Passa pela mesma conversa da seção 6 (o mesmo paciente, o mesmo estado).
- **Foto** = `message.imageMessage` presente (ou `messageType: "imageMessage"`): registra no diário do paciente `{tipo: "foto", mimetype: imageMessage.mimetype, caption: imageMessage.caption ou null, message_id: key.id}` (seção 10) e responde texto contendo `foto` e `registrad`; telefone sem paciente → resposta contém `cadastro`. **Nunca** baixa, pede à Evolution (o endpoint dela de obter mídia em base64 fica proibido no código, inclusive em comentário — o `verificar-limites.sh` grepa o nome dele) nem guarda a mídia: só esses metadados.
- Sem texto nem foto (áudio, documento, figurinha...) → responde `Por enquanto só consigo ler mensagens de texto e fotos.`
- Telefone = dígitos do `remoteJid` antes do `@`, normalizado como na seção 5.
- Cada resposta da conversa vai por `POST {EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCIA}` com header `apikey: {EVOLUTION_API_KEY}` e corpo `{"number": "<dígitos com 55>", "text": "<texto>"}`, na ordem.

**Saída** (confirmação, espera, retorno, lembrete, plano, campanha, humano): com a Evolution configurada, cada mensagem da caixa de saída é enviada do mesmo jeito. Em `/api/saida` cada mensagem tem `status`: `enviado` (2xx), `pendente` (erro HTTP ou de conexão) ou `simulado`. `POST /api/tarefas/rodar` reenvia as `pendente` e devolve `"reenviadas": n` (as que viraram `enviado`). Rotas síncronas: seção 5.

## 20. Atendimento interno pelo Telegram

Variáveis: `TELEGRAM_API_URL` (ex.: `https://api.telegram.org` — só nesta spec e no README; nunca no código nem no `.env.exemplo`), `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` (grupo da equipe), `TELEGRAM_SEGREDO`. Sem elas, nada vai ao Telegram (o resto funciona igual). Envio: `POST {TELEGRAM_API_URL}/bot{TELEGRAM_TOKEN}/sendMessage` com `{"chat_id", "text"[, "reply_to_message_id"]}`; a resposta do Telegram traz `result.message_id`.

**Atendimento humano** (`/api/atendimento-humano`, seção 5):
- Ao abrir (pedido de atendente, emergência, alerta, dúvida fora do plano, 2º "não entendi"): manda ao grupo um texto com `#<id>`, telefone, nome (se houver), motivo, a última mensagem do paciente e, se `prioridade` for `alta`, a palavra `ALTA`. Guarda o `message_id`. Um telefone tem no máximo **um** atendimento `aberto`; nova causa enquanto aberto não abre outro (mas emergência/alerta elevam a prioridade para `alta`).
- Enquanto o atendimento do telefone estiver `aberto`, o bot **não responde** sozinho (`respostas: []`), exceto regras 1 e 2 da seção 6; cada mensagem do paciente vai ao grupo como `#<id> <nome ou telefone>: <texto>`, em resposta (`reply_to_message_id`) à mensagem de abertura.
- `POST /webhook/telegram` exige header `X-Telegram-Bot-Api-Secret-Token: {TELEGRAM_SEGREDO}` (senão 401). Só aceita updates com `message.chat.id` igual a `TELEGRAM_CHAT_ID` (comparados como **texto**); os outros são ignorados (200, sem efeito).
- Mensagem da equipe que é resposta (`reply_to_message.message_id`) a uma mensagem do atendimento `#id` → o texto vai ao paciente (caixa de saída `tipo: "humano"`, e pela Evolution se configurada).
- Comandos: `/responder <id> <texto>` (o mesmo, sem precisar responder em cima); `/encerrar <id>` → status `encerrado`, o bot volta a responder aquele telefone; `/fila` → o bot manda a lista dos abertos (cada um com `#id`); `/alertas` → só os abertos com `prioridade: "alta"` (cada um com `#id` e o motivo); nenhum → texto contém `nenhum`; `/agenda [AAAA-MM-DD]` (padrão: hoje pelo relógio) → manda os agendamentos ativos do dia, uma linha `HH:MM <nome do paciente> — <nome do serviço> (<nome do profissional>)` cada, com o sufixo ` [online]` quando a consulta é online.
- Pela página [E]: `POST /api/atendimento-humano/{id}/responder {texto}` e `POST /api/atendimento-humano/{id}/encerrar` fazem o mesmo.
- **Avisos à equipe:** agendamento feito pelo chat → `Novo agendamento: DD/MM HH:MM <nome> — <serviço> com <profissional>` (mais ` (online)` quando online); cancelamento pelo chat → texto começando com `Cancelado:` e com `DD/MM HH:MM`.

## 21. Docker / VPS

- `Dockerfile` (imagem oficial `python:3-slim` ou similar, **sem `pip install`**) que roda `./atende serve --host 0.0.0.0 --porta 8080 --dados /dados`, com `HEALTHCHECK` em `/api/saude` (a imagem não tem `curl`: usar `python3 -c` com `urllib`). O container precisa subir **sem volume** em `/dados` (a verificação independente faz `docker run` sem `-v`): o `serve` cria a pasta (seção 1).
- `docker-compose.yml` com o serviço `atende`: `build: .`, `restart: unless-stopped`, `env_file: .env`, volume para `/dados`, porta publicada só em `127.0.0.1:8080` (na VPS fica atrás de proxy reverso com HTTPS).
- `.env.exemplo` com todas as variáveis das seções 19 e 20, **valores vazios** (`VARIAVEL=` e nada depois do `=`; nenhum segredo, nenhuma URL, e a palavra `http` não aparece em linha nenhuma — nem em comentário).
- `README.md` com a seção **Deploy na VPS** (acrescentada pelo implementador **sem remover** a seção "Como rodar no seu ambiente"): subir o compose, proxy HTTPS, configurar o webhook da Evolution para `/webhook/evolution/<segredo>` (evento `MESSAGES_UPSERT`), registrar o webhook do Telegram com `setWebhook` + `secret_token`, e o backup diário (`./atende backup` no cron).
