# atende-nutricao

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Atende Nutrição](guia/assets/banner-en.jpg)](https://inematds.github.io/atende-nutricao/guia/en/)

## 📖 User guide

Landing page and step-by-step guide: **https://inematds.github.io/atende-nutricao/guia/en/** · [Português](https://inematds.github.io/atende-nutricao/guia/) · [Español](https://inematds.github.io/atende-nutricao/guia/es/)

A patient care system for **a nutrition practice**, in Python 3 with the standard library and SQLite: appointment scheduling (first visit and follow-ups, in person or online with a link supplied by the team), automatic confirmation, waitlist, scheduled follow-up, a **meal plan** entered by the nutritionist and queried by the patient in the chat, a **diary** (water, meals done or skipped, weight, meal photo as metadata) with opt-in reminders and goals, FAQ, a human queue on Telegram, warning signs, campaigns with a minimal advertising guardrail, LGPD for health data (the Brazilian data protection law), records, backup and a monthly export to the Recovery Dashboard of **Raio-X de Margem** (`clinica` package). Base: `atende-clinica`, adapted.

**Status (05/10/2026): planned, not implemented.** What exists is the contract (`docs/ESPECIFICACAO.md`), 99 black-box acceptance tests (`tests/`), the decisions with default proposals (`docs/DECISOES-ABERTAS.md`), the map of Raio-X leaks (`docs/MAPA-RAIO-X.md`) and the long-run folder (`longrun/2026-10-05-nutri-v1/`), ready for anyone to run the implementation in their own environment with an agent.

Note: the docs, tests and the bot's chat commands are in Portuguese. LGPD, `192` (emergency services) and `188` (CVV) are Brazilian; in another country the practice must swap in its local emergency contacts and privacy law.

## What the system does (v1)

- **Scheduling:** a grid per professional, first visit/follow-up/bioimpedance, in person or **online** (the link supplied by the team goes into the confirmation and the chat), no double booking (concurrent requests: one 201, the rest 409), blocked time, rescheduling, attended/no-show.
- **Conversation** (web chat and WhatsApp through Evolution): book through the chat, confirm with `1`/`2`, waitlist, FAQ, `meu plano` (my plan) / `o que posso comer no lanche da tarde` (what can I eat at the afternoon snack; answers only what is in the patient's plan), log `2 copos` (2 glasses), `pulei o almoço` (I skipped lunch), `peso 82,5` (weight 82.5; neutral reply, no judgment), `link` for the online visit, a human attendant, `PARAR` (stop), `parar lembretes` (stop reminders).
- **Bot limits:** it never prescribes a diet, supplement or calculation; a question outside the plan/FAQ goes to a human; warning signs (physical: 192; binge eating/purging/suicidal thoughts: 188) open a high-priority queue entry.
- **Meal plan:** meals by time with options and notes, versions, sent to the patient by the team; no nutrition calculation in v1.
- **Diary and goals:** weight series with the change, glasses of water against a goal, meal adherence, a photo as a record (metadata only), reminders for water and for the plan's meals at chosen times, with a tolerance window.
- **Team:** an `/equipe` page with a token (schedule, patients, plan, diary/adherence, weight series, FAQ, human queue); Telegram with `/agenda`, `/alertas`, `/fila`, `/responder`, `/encerrar` and notices for new and cancelled bookings.
- **LGPD and Raio-X:** export and erase a patient's health data; campaigns only with consent and a minimal guardrail (⚠ CFN to be confirmed by the owner); `GET /api/raiox?mes=` and the CLI `raiox --acompanhamento` with the ids of the `clinica` package; backup/restore; Docker.

What stays out of v1 is in section 14 of the specification.

## How to run it in your own environment

### Prerequisites

- Linux/macOS with `git`, `python3` ≥ 3.10 and `pytest` (`pip install pytest`; it is a development tool, the application does not depend on it).
- An agent on your **subscription**: Codex CLI (`codex`) or Claude Code (`claude`). No API is called.
- For the final independent verification: `docker`.
- Long-run method and tools: a clone of `~/projetos/execucao-longa` (`tools/loop-longrun.sh`, `docs/PLANO-EXECUCAO-LONGA.md`). If you do not have it, the interactive `/goal` route (below) does not need it.

### 1. Answer the decisions and freeze the contract

```sh
cd atende-nutricao
# read docs/DECISOES-ABERTAS.md; "ok em tudo" (all fine) = nothing to change
python3 -m pytest -q --collect-only | tail -n 1     # 99 tests collected
bash longrun/2026-10-05-nutri-v1/congelar.sh        # writes hash-congelado.txt and makes 1 commit
```

If you change anything marked ⚠ in the decisions, edit `docs/ESPECIFICACAO.md` and the tests **before** freezing. Once frozen, the contract and tests are protected: the agent does not change them; if a test contradicts the spec, it records it in `failures.md` and stops (human gate).

### 2a. Headless loop (Codex `gpt-6-astra`)

```sh
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-nutri-v1
```

Configuration lives in `longrun/2026-10-05-nutri-v1/loop.env` (quick/final test, protected files, 20 cycles × 30 min, 8 GB, a stop after 3 cycles with no progress, `CODEX_ARGS` opening a local socket in the sandbox). The loop uses `flock`, `timeout` and `MemoryMax`, reverts any cycle that touches a protected file, commits a checkpoint per cycle and stops on its own when the final test passes.

### 2b. `/goal` in the Codex TUI

```sh
codex -c sandbox_workspace_write.network_access=true
```

Paste the contents of `longrun/2026-10-05-nutri-v1/prompt-goal-codex.md`. Follow with `/goals`; pause/resume with `/goal pause|resume`.

### 2c. `/goal` in Claude Code

Open a new session in the project folder and follow `longrun/2026-10-05-nutri-v1/prompt-goal-claude.md` (the `/goal` condition + the same Codex block as the first message).

### 3. Follow along

```sh
tail -n 20 longrun/2026-10-05-nutri-v1/loop.log        # headless
cat longrun/2026-10-05-nutri-v1/state.md               # What works / What is missing / How to resume
tail -n 5 longrun/2026-10-05-nutri-v1/progress.md
python3 -m pytest -q tests/ | tail -n 3
```

Done = `python3 -m pytest -q tests/` → **99 passed** and `bash longrun/2026-10-05-nutri-v1/verificar-limites.sh` → **LIMITES OK** (contract hash intact, same number of tests, `hash-congelado.txt` equal to the one written by the freeze commit, only in-scope files, no external dependency, no external URL, no key, no media download, no `0.0.0.0` in the code).

### 4. Independent verification (level 4, human)

```sh
python3 longrun/2026-10-05-nutri-v1/verificar-independente.py   # INDEPENDENTE OK
```

It looks for fixture values copied into the code, brings up a practice it has never seen (20-minute step, 40-minute visit, follow-up after 15 days, no online visits, a meal plan with differently named meals, another clock) and checks rules that only pass if the logic is general (scheduling, chat, plan, weight, water, meals, reminders, follow-up, the campaign guardrail, concurrency, Raio-X, LGPD); then it runs `docker build` and tests the container healthcheck. Open `/` and `/equipe` in the browser.

## Running (after it is implemented)

```sh
mkdir -p dados && cp exemplos/nutricao.json dados/nutricao.json   # replace TROQUE-ESTE-TOKEN
./atende serve --porta 8080 --dados dados
```

The patient chat is at `/`, the team page at `/equipe` (header `X-Token`). `ATENDE_AGORA` pins the clock for tests only. The deploy section (compose, HTTPS proxy, the Evolution and Telegram webhooks, daily backup) is written by the implementer according to section 21 of the specification.

## Files

- `docs/ESPECIFICACAO.md` — the contract (21 sections, route table, rules with boundaries, out of v1).
- `docs/DECISOES-ABERTAS.md` — decisions with a default proposal; questions for the owner (including the ⚠ about the CFN).
- `docs/MAPA-RAIO-X.md` — each leak in the `clinica` package → a v1 piece or the reason it stays out.
- `docs/VALIDACAO.md` — adversarial validation of the plan (05/10/2026): test × spec checklist, verified arithmetic, output of the guardrail/harness checks.
- `tests/` — 99 black-box tests (`conftest.py` starts the CLI, a fixed clock, a fake Evolution/Telegram server). Fixture in `tests/fixtures/nutricao.json`; a copy in `exemplos/`.
- `longrun/2026-10-05-nutri-v1/` — goal (level 3+), plan, state, channel, loop.env, prompts, `congelar.sh`, `verificar-limites.sh`, `verificar-independente.py`.
- `FALHAS.md` — one line per failure (date, what broke, smallest fix, prompt | infra).
