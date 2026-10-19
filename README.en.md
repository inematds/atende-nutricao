# atende-nutricao

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Atende Nutrição](guia/assets/banner.jpg)](https://inematds.github.io/atende-nutricao/guia/)

## 📖 User guide

Landing page and step-by-step guide (PT/EN/ES): **https://inematds.github.io/atende-nutricao/guia/** · [English](https://inematds.github.io/atende-nutricao/guia/en/) · [Español](https://inematds.github.io/atende-nutricao/guia/es/)

A patient care system for **a single nutrition practice**, in Python 3 with the standard library and SQLite: appointment scheduling (first consultation and follow-ups, in person or online with a link provided by the staff), automatic confirmation, waiting list, scheduled follow-up, **meal plan** recorded by the nutritionist and queried by the patient in the conversation, **diary** (water, meals eaten/skipped, weight, meal photo by metadata) with opt-in reminders and goals, FAQ, human queue on Telegram, warning signs, campaigns with a minimum advertising safeguard, LGPD for health data, registrations, backup, and monthly export to the Recovery Panel of **Raio-X de Margem** (`clinica` package). Base: `atende-clinica`, adapted.

**Status (10/19/2026): v0.8.0 implemented.** Backend, web chat (`/`) and staff area (`/equipe`), Evolution, Telegram, Docker, and VPS instructions; 99/99 tests pass, `verificar-limites.sh` → LIMITES OK and `verificar-independente.py` → INDEPENDENTE OK (includes `docker build` and healthcheck). Deployment to the VPS is done by the person in charge. Detailed status in `longrun/2026-10-05-nutri-v1/state.md`.

## What the system does (v1)

- **Scheduling:** grid per professional, first consultation/follow-up/bioimpedance, in person or **online** (link provided by the staff goes into the confirmation and the chat), no double booking (concurrent requests: one 201, the others 409), blocks, rescheduling, attendance/no-show.
- **Conversation** (web chat and WhatsApp via Evolution): schedule through the chat, confirm with `1`/`2`, waiting list, FAQ, `meu plano` / `o que posso comer no lanche da tarde` (answers only what is in the patient's plan), log `2 copos`, `pulei o almoço`, `peso 82,5` (neutral reply, no judgment), `link` for the online consultation, human attendant, `PARAR`, `parar lembretes`.
- **Bot limits:** never prescribes diets, supplements, or calculations; questions outside the plan/FAQ go to a human; warning signs (physical → 192; binge eating/purging/suicidal ideation → 188) open a queue with high priority.
- **Meal plan:** meals by time with options and notes, versions, sent to the patient by the staff; no nutritional calculation in v1.
- **Diary and goals:** weight series with variation, glasses of water with a goal, meal adherence, photo as a record (metadata only), reminders for water and for the plan's meals at chosen times, with a tolerance window.
- **Staff:** `/equipe` page with token (schedule, patients, plan, diary/adherence, weight series, FAQ, human queue); Telegram with `/agenda`, `/alertas`, `/fila`, `/responder`, `/encerrar` and scheduling/cancellation notices.
- **LGPD and Raio-X:** export and delete the patient's health data; campaign only with consent and minimum safeguard (⚠ CFN to be confirmed by the owner); `GET /api/raiox?mes=` and CLI `raiox --acompanhamento` with the ids of the `clinica` package; backup/restore; Docker.

What is left out of v1 is in section 14 of the specification.

## How to run in your environment

### Prerequisites

- Linux/macOS with `git` and `python3` ≥ 3.10. The application has no external dependencies.
- `pytest` only to run the tests (`pip install pytest`; it is a development tool).
- `docker` (with Compose) for the independent verification and the VPS deployment.
- Evolution and the Telegram bot are optional: without the variables, WhatsApp uses a simulated outbox and nothing is sent to Telegram.

### 1. Check the tests

```sh
git clone https://github.com/inematds/atende-nutricao && cd atende-nutricao
python3 -m pytest -q tests/ | tail -n 1     # 99 passed
./atende --help                             # serve, raiox, backup, restaurar
```

### 2. Run

```sh
mkdir -p dados && cp exemplos/nutricao.json dados/nutricao.json   # troque TROQUE-ESTE-TOKEN
./atende serve --porta 8080 --dados dados
```

The patient chat is at `/`, the staff page at `/equipe` (header `X-Token`). `ATENDE_AGORA` fixes the clock for tests only. Before using with patients, read `docs/DECISOES-ABERTAS.md`: the items marked with ⚠ (campaign safeguard, warning words, weight rules, CFN rules) require the owner's confirmation. The deployment (compose, HTTPS proxy, Evolution and Telegram webhooks, daily backup) is in the [VPS Deployment](#vps-deployment) section.

### 3. Verifications

```sh
bash longrun/2026-10-05-nutri-v1/verificar-limites.sh            # LIMITES OK at close; now flags only guia/ and README.en/es (docs added later)
python3 longrun/2026-10-05-nutri-v1/verificar-independente.py   # INDEPENDENTE OK
```

`verificar-limites.sh` checks the contract hash, the number of tests, `hash-congelado.txt` identical to the one recorded by the freeze commit, only in-scope files, no external dependency, no external URL, no key, no media download, no `0.0.0.0` in the code. `verificar-independente.py` looks for fixture values copied into the code, brings up a never-before-seen practice (20-minute step, 40-minute consultation, follow-up in 15 days, no online appointments, plan with meals under other names, a different clock) and checks rules that only pass if the logic is general — scheduling, chat, plan, weight, water, meal, reminder, follow-up, campaign safeguard, concurrency, Raio-X, LGPD —; then it runs `docker build` and tests the container's healthcheck.

## How it was built (and how to redo or adapt it)

The system was built with the long-execution method (`~/projetos/execucao-longa`): first the contract (`docs/ESPECIFICACAO.md`), the proposed decisions, and the 99 black-box tests; then the hash freeze (`longrun/2026-10-05-nutri-v1/congelar.sh`); then an agent on a **subscription** (Codex or Claude Code, no API) worked in cycles until `99 passed`, `LIMITES OK`, and `INDEPENDENTE OK`. With the contract frozen, tests and specification were protected: the agent could not change them; a test conflicting with the spec went to `failures.md` (human gate).

To adapt it to another practice or change a rule marked with ⚠, the method remains in the repository: edit `docs/ESPECIFICACAO.md` and the tests, freeze again, and run one of the paths below.

```sh
bash longrun/2026-10-05-nutri-v1/congelar.sh                                  # grava hash-congelado.txt e faz 1 commit
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-nutri-v1   # loop headless (Codex gpt-6-astra)
```

- The loop uses `longrun/2026-10-05-nutri-v1/loop.env` (20 cycles × 30 min, 8 GB, stops after 3 cycles without progress, `CODEX_ARGS` allowing local sockets in the sandbox); it does `flock`, `timeout`, `MemoryMax`, reverts any cycle that touches a protected file, commits a checkpoint per cycle, and stops by itself when the final test passes.
- `/goal` in Codex TUI: `codex -c sandbox_workspace_write.network_access=true` and paste `longrun/2026-10-05-nutri-v1/prompt-goal-codex.md`.
- `/goal` in Claude Code: new session in the project folder, following `longrun/2026-10-05-nutri-v1/prompt-goal-claude.md`.
- Monitoring: `longrun/2026-10-05-nutri-v1/loop.log`, `state.md` (Works / Missing / How to resume), and `progress.md`.

## Files

- `docs/ESPECIFICACAO.md` — contract (21 sections, route table, rules with boundaries, out of v1).
- `docs/DECISOES-ABERTAS.md` — decisions with a default proposal; questions for the owner (including the CFN ⚠).
- `docs/MAPA-RAIO-X.md` — each leak of the `clinica` package → v1 piece or reason for being left out.
- `docs/VALIDACAO.md` — adversarial validation of the plan (10/05/2026): test × spec checklist, verified calculations, output of the safeguard/harness checks.
- `tests/` — 99 black-box tests (`conftest.py` brings up the CLI, fixed clock, fake Evolution/Telegram server). Fixture in `tests/fixtures/nutricao.json`; copy in `exemplos/`.
- `longrun/2026-10-05-nutri-v1/` — goal (level 3+), plan, state, channel, loop.env, prompts, `congelar.sh`, `verificar-limites.sh`, `verificar-independente.py`.
- `FALHAS.md` — one line per failure (date, what broke, smallest fix, prompt | infra).

## VPS Deployment

Run these steps on the VPS with Docker and Compose installed. Publishing and configuring the integrations are done by the person in charge of the practice.

### Prepare and start

In the project folder:

```sh
umask 077
cp .env.exemplo .env
mkdir -p dados backups
# Apenas na primeira instalação (não sobrescreva uma configuração existente):
test -f dados/nutricao.json || cp exemplos/nutricao.json dados/nutricao.json
chmod 700 dados backups
chmod 600 .env dados/nutricao.json
```

Edit `dados/nutricao.json`: replace `TROQUE-ESTE-TOKEN` with your own secret and adjust the practice, professionals, services, and schedules. Professionals, services, and FAQ seed the database only on the first run; afterwards they are changed through the API. Leave `ATENDE_AGORA` unset in production.

```sh
docker compose up -d --build
docker compose ps
docker compose logs --tail=30 atende
```

The `./dados:/dados` volume keeps the database and the configuration across restarts; `./backups:/backups` receives the backups. The image also creates `/dados` when started without a volume. The healthcheck queries `/api/saude` with Python, without installing dependencies.

### HTTPS proxy

Configure in the VPS reverse proxy a domain with a TLS certificate and forwarding to `127.0.0.1:8080`. The port published by Compose stays on loopback only. Forward the paths `/`, `/equipe`, `/api/`, and `/webhook/`, preserving the `X-Token` and `X-Telegram-Bot-Api-Secret-Token` headers. The proxy configuration depends on the domain and the server already used on the VPS.

### Evolution and Telegram

Without the variables filled in, WhatsApp uses the simulated outbox and no notice is sent to Telegram. Configure in `.env` only the services you will use:

- Evolution: `EVOLUTION_URL` must be the address reachable **from inside the container**, together with `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCIA`, and `WEBHOOK_SEGREDO`. In the Evolution panel, configure the webhook of the HTTPS domain at the path `/webhook/evolution/<segredo>`, with the event `MESSAGES_UPSERT`. The path secret must match `WEBHOOK_SEGREDO`. Photos are recorded by metadata only.
- Telegram: fill in `TELEGRAM_API_URL`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, and `TELEGRAM_SEGREDO`. Register the webhook with the bot's `setWebhook` method: send `url` with the domain's HTTPS address followed by `/webhook/telegram` and `secret_token` with the same value as `TELEGRAM_SEGREDO`. Telegram will send this secret in its own header. Add the bot to the group defined in `TELEGRAM_CHAT_ID`.

Recreate the service after changing the environment: `docker compose up -d --force-recreate atende`. The integration secrets are different from the staff token in `nutricao.json`. Do not publish the `.env` or the patients' data.

### Tasks and daily backup

Tasks are explicit: schedule an authenticated local call to `POST /api/tarefas/rodar` every minute for confirmations, follow-ups, reminders, and resends. The body is `{}`; use the practice token in the `X-Token` header. Do not provide `agora` in production. Repeated runs are idempotent.

To create a consistent copy of the SQLite database while the server is running:

```sh
docker compose exec -T atende ./atende backup --dados /dados --saida /backups/estado.sqlite3
```

Example of a daily cron at 03:15 (adjust `/srv/atende-nutricao` to the real folder; escaping `%` is required in crontab):

```cron
15 3 * * * cd /srv/atende-nutricao && docker compose exec -T atende ./atende backup --dados /dados --saida /backups/estado-$(date +\%F).sqlite3
```

Also keep protected copies of `dados/nutricao.json` and `.env`: the database backup does not include these files. Define retention and a secure copy outside the VPS. To restore, stop the service first and choose the desired file:

```sh
docker compose stop atende
docker compose run --rm --no-deps atende ./atende restaurar --dados /dados --entrada /backups/estado.sqlite3
docker compose up -d atende
```
