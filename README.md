# atende-nutricao

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Atende Nutrição](guia/assets/banner.jpg)](https://inematds.github.io/atende-nutricao/guia/)

## 📖 Guia de uso

Landing e guia passo a passo (PT/EN/ES): **https://inematds.github.io/atende-nutricao/guia/** · [English](https://inematds.github.io/atende-nutricao/guia/en/) · [Español](https://inematds.github.io/atende-nutricao/guia/es/)

Sistema de atendimento ao paciente para **um consultório de nutrição**, em Python 3 com biblioteca padrão e SQLite: agenda de consultas (primeira consulta e retornos, presencial ou online com link informado pela equipe), confirmação automática, lista de espera, retorno programado, **plano alimentar** registrado pelo nutricionista e consultado pelo paciente na conversa, **diário** (água, refeições feitas/puladas, peso, foto de refeição por metadados) com lembretes opt-in e metas, FAQ, fila humana no Telegram, sinais de alerta, campanhas com trava mínima de publicidade, LGPD de dado de saúde, cadastros, backup e exportação mensal para o Painel de Recuperação do **Raio-X de Margem** (pacote `clinica`). Base: o `atende-clinica`, adaptado.

**Estado (19/10/2026): v0.8.0 implementada.** Backend, chat web (`/`) e área da equipe (`/equipe`), Evolution, Telegram, Docker e instruções de VPS; 99/99 testes passam, `verificar-limites.sh` → LIMITES OK e `verificar-independente.py` → INDEPENDENTE OK (inclui `docker build` e healthcheck). Deploy na VPS é feito pelo responsável. Estado detalhado em `longrun/2026-10-05-nutri-v1/state.md`.

## O que o sistema faz (v1)

- **Agenda:** grade por profissional, primeira consulta/retorno/bioimpedância, presencial ou **online** (link informado pela equipe entra na confirmação e no chat), sem horário duplo (pedidos concorrentes: um 201, os outros 409), bloqueios, remarcação, presença/falta.
- **Conversa** (chat web e WhatsApp pela Evolution): agendar pelo chat, confirmar com `1`/`2`, lista de espera, FAQ, `meu plano` / `o que posso comer no lanche da tarde` (responde só o que está no plano do paciente), registrar `2 copos`, `pulei o almoço`, `peso 82,5` (resposta neutra, sem julgamento), `link` da consulta online, atendente humano, `PARAR`, `parar lembretes`.
- **Limites do bot:** nunca prescreve dieta, suplemento ou cálculo; dúvida fora do plano/FAQ vai para o humano; sinais de alerta (físicos → 192; compulsão/purgação/ideação → 188) abrem fila com prioridade alta.
- **Plano alimentar:** refeições por horário com opções e observações, versões, envio ao paciente pela equipe; sem cálculo nutricional no v1.
- **Diário e metas:** série de peso com variação, copos de água com meta, adesão às refeições, foto como registro (só metadados), lembretes de água e das refeições do plano em horários escolhidos, com janela de tolerância.
- **Equipe:** página `/equipe` com token (agenda, pacientes, plano, diário/adesão, série de peso, FAQ, fila humana); Telegram com `/agenda`, `/alertas`, `/fila`, `/responder`, `/encerrar` e avisos de agendamento/cancelamento.
- **LGPD e Raio-X:** exportar e apagar o dado de saúde do paciente; campanha só com consentimento e trava mínima (⚠ CFN a confirmar pelo dono); `GET /api/raiox?mes=` e CLI `raiox --acompanhamento` com os ids do pacote `clinica`; backup/restauração; Docker.

O que fica de fora do v1 está na seção 14 da especificação.

## Como rodar no seu ambiente

### Pré-requisitos

- Linux/macOS com `git` e `python3` ≥ 3.10. A aplicação não tem dependências externas.
- `pytest` só para rodar os testes (`pip install pytest`; é ferramenta de desenvolvimento).
- `docker` (com Compose) para a verificação independente e o deploy na VPS.
- Evolution e bot do Telegram são opcionais: sem as variáveis, o WhatsApp usa caixa de saída simulada e nada é enviado ao Telegram.

### 1. Conferir os testes

```sh
git clone https://github.com/inematds/atende-nutricao && cd atende-nutricao
python3 -m pytest -q tests/ | tail -n 1     # 99 passed
./atende --help                             # serve, raiox, backup, restaurar
```

### 2. Executar

```sh
mkdir -p dados && cp exemplos/nutricao.json dados/nutricao.json   # troque TROQUE-ESTE-TOKEN
./atende serve --porta 8080 --dados dados
```

O chat do paciente fica em `/`, a página da equipe em `/equipe` (header `X-Token`). `ATENDE_AGORA` fixa o relógio só para testes. Antes de usar com pacientes, leia `docs/DECISOES-ABERTAS.md`: os itens marcados com ⚠ (trava de campanha, palavras de alerta, regras do peso, regras do CFN) pedem a confirmação do dono. O deploy (compose, proxy HTTPS, webhooks da Evolution e do Telegram, backup diário) está na seção [Deploy na VPS](#deploy-na-vps).

### 3. Verificações

```sh
bash longrun/2026-10-05-nutri-v1/verificar-limites.sh            # LIMITES OK no fechamento; hoje acusa só guia/ e README.en/es (docs posteriores)
python3 longrun/2026-10-05-nutri-v1/verificar-independente.py   # INDEPENDENTE OK
```

`verificar-limites.sh` confere o hash do contrato, o nº de testes, `hash-congelado.txt` igual ao gravado pelo commit de congelamento, só arquivos do escopo, sem dependência externa, sem URL externa, sem chave, sem download de mídia, sem `0.0.0.0` no código. `verificar-independente.py` procura valores do fixture copiados no código, sobe um consultório nunca visto (passo de 20 min, consulta de 40 min, retorno em 15 dias, sem atendimento online, plano com refeições de outros nomes, outro relógio) e confere regras que só passam se a lógica for geral — agenda, chat, plano, peso, água, refeição, lembrete, retorno, trava de campanha, concorrência, Raio-X, LGPD —; depois faz `docker build` e testa o healthcheck do container.

## Como foi feito (e como refazer ou adaptar)

O sistema foi construído pelo método de execução longa (`~/projetos/execucao-longa`): primeiro o contrato (`docs/ESPECIFICACAO.md`), as decisões propostas e os 99 testes caixa-preta; depois o congelamento por hash (`longrun/2026-10-05-nutri-v1/congelar.sh`); então um agente pela **assinatura** (Codex ou Claude Code, nenhuma API) trabalhou em ciclos até `99 passed`, `LIMITES OK` e `INDEPENDENTE OK`. Com o contrato congelado, testes e especificação ficaram protegidos: o agente não podia alterá-los; teste em conflito com a spec ia para `failures.md` (portão humano).

Para adaptar a outro consultório ou mudar uma regra marcada com ⚠, o método continua no repositório: edite `docs/ESPECIFICACAO.md` e os testes, congele de novo e rode um dos caminhos abaixo.

```sh
bash longrun/2026-10-05-nutri-v1/congelar.sh                                  # grava hash-congelado.txt e faz 1 commit
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-nutri-v1   # loop headless (Codex gpt-6-astra)
```

- O loop usa `longrun/2026-10-05-nutri-v1/loop.env` (20 ciclos × 30 min, 8 GB, parada após 3 ciclos sem avanço, `CODEX_ARGS` liberando socket local no sandbox); faz `flock`, `timeout`, `MemoryMax`, reverte ciclo que mexer em arquivo protegido, commita checkpoint por ciclo e para sozinho quando o teste final passa.
- `/goal` no Codex TUI: `codex -c sandbox_workspace_write.network_access=true` e cole `longrun/2026-10-05-nutri-v1/prompt-goal-codex.md`.
- `/goal` no Claude Code: sessão nova na pasta do projeto, seguindo `longrun/2026-10-05-nutri-v1/prompt-goal-claude.md`.
- Acompanhar: `longrun/2026-10-05-nutri-v1/loop.log`, `state.md` (Funciona / Falta / Como retomar) e `progress.md`.

## Arquivos

- `docs/ESPECIFICACAO.md` — contrato (21 seções, tabela de rotas, regras com fronteiras, fora do v1).
- `docs/DECISOES-ABERTAS.md` — decisões com proposta padrão; perguntas para o dono (inclusive o ⚠ do CFN).
- `docs/MAPA-RAIO-X.md` — cada vazamento do pacote `clinica` → peça do v1 ou motivo de ficar fora.
- `docs/VALIDACAO.md` — validação adversarial do plano (05/10/2026): checklist teste × spec, contas conferidas, saída dos checks de trava/harness.
- `tests/` — 99 testes caixa-preta (`conftest.py` sobe o CLI, relógio fixo, servidor falso de Evolution/Telegram). Fixture em `tests/fixtures/nutricao.json`; cópia em `exemplos/`.
- `longrun/2026-10-05-nutri-v1/` — goal (nível 3+), plan, state, canal, loop.env, prompts, `congelar.sh`, `verificar-limites.sh`, `verificar-independente.py`.
- `FALHAS.md` — uma linha por falha (data, o que quebrou, menor correção, prompt | infra).

## Deploy na VPS

Execute estes passos na VPS com Docker e Compose instalados. A publicação e a configuração das integrações são feitas pelo responsável pelo consultório.

### Preparar e subir

Na pasta do projeto:

```sh
umask 077
cp .env.exemplo .env
mkdir -p dados backups
# Apenas na primeira instalação (não sobrescreva uma configuração existente):
test -f dados/nutricao.json || cp exemplos/nutricao.json dados/nutricao.json
chmod 700 dados backups
chmod 600 .env dados/nutricao.json
```

Edite `dados/nutricao.json`: substitua `TROQUE-ESTE-TOKEN` por um segredo próprio e ajuste o consultório, profissionais, serviços e horários. Profissionais, serviços e FAQ semeiam o banco somente na primeira execução; depois são alterados pela API. Deixe `ATENDE_AGORA` ausente em produção.

```sh
docker compose up -d --build
docker compose ps
docker compose logs --tail=30 atende
```

O volume `./dados:/dados` mantém o banco e a configuração entre reinícios; `./backups:/backups` recebe os backups. A imagem também cria `/dados` quando iniciada sem volume. O healthcheck consulta `/api/saude` com Python, sem instalar dependências.

### Proxy HTTPS

Configure no proxy reverso da VPS um domínio com certificado TLS e encaminhamento para `127.0.0.1:8080`. A porta publicada pelo Compose fica somente em loopback. Encaminhe os caminhos `/`, `/equipe`, `/api/` e `/webhook/`, preservando os headers `X-Token` e `X-Telegram-Bot-Api-Secret-Token`. A configuração do proxy depende do domínio e do servidor já usados na VPS.

### Evolution e Telegram

Sem as variáveis preenchidas, o WhatsApp usa a caixa de saída simulada e nenhum aviso é enviado ao Telegram. Configure no `.env` somente os serviços que for usar:

- Evolution: `EVOLUTION_URL` deve ser o endereço acessível **de dentro do container**, junto de `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCIA` e `WEBHOOK_SEGREDO`. No painel da Evolution, configure o webhook do domínio HTTPS no caminho `/webhook/evolution/<segredo>`, com evento `MESSAGES_UPSERT`. O segredo do caminho deve coincidir com `WEBHOOK_SEGREDO`. Fotos são registradas apenas por metadados.
- Telegram: preencha `TELEGRAM_API_URL`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` e `TELEGRAM_SEGREDO`. Registre o webhook com o método `setWebhook` do bot: envie `url` com o endereço HTTPS do domínio seguido de `/webhook/telegram` e `secret_token` com o mesmo valor de `TELEGRAM_SEGREDO`. O Telegram enviará esse segredo no header próprio. Inclua o bot no grupo definido em `TELEGRAM_CHAT_ID`.

Recrie o serviço após alterar o ambiente: `docker compose up -d --force-recreate atende`. Os segredos das integrações são diferentes do token da equipe em `nutricao.json`. Não publique o `.env` ou os dados dos pacientes.

### Tarefas e backup diário

As tarefas são explícitas: programe uma chamada local autenticada a `POST /api/tarefas/rodar` a cada minuto para confirmações, retornos, lembretes e reenvios. O corpo é `{}`; use o token do consultório no header `X-Token`. Não informe `agora` em produção. Rodadas repetidas são idempotentes.

Para criar uma cópia consistente do SQLite com o servidor ligado:

```sh
docker compose exec -T atende ./atende backup --dados /dados --saida /backups/estado.sqlite3
```

Exemplo de cron diário às 03:15 (ajuste `/srv/atende-nutricao` para a pasta real; o escape de `%` é necessário no crontab):

```cron
15 3 * * * cd /srv/atende-nutricao && docker compose exec -T atende ./atende backup --dados /dados --saida /backups/estado-$(date +\%F).sqlite3
```

Guarde também cópias protegidas de `dados/nutricao.json` e `.env`: o backup do banco não inclui esses arquivos. Defina retenção e cópia segura fora da VPS. Para restaurar, pare o serviço antes e escolha o arquivo desejado:

```sh
docker compose stop atende
docker compose run --rm --no-deps atende ./atende restaurar --dados /dados --entrada /backups/estado.sqlite3
docker compose up -d atende
```
