# atende-nutricao

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Atende Nutrição](guia/assets/banner.jpg)](https://inematds.github.io/atende-nutricao/guia/)

## 📖 Guia de uso

Landing e guia passo a passo (PT/EN/ES): **https://inematds.github.io/atende-nutricao/guia/** · [English](https://inematds.github.io/atende-nutricao/guia/en/) · [Español](https://inematds.github.io/atende-nutricao/guia/es/)

Sistema de atendimento ao paciente para **um consultório de nutrição**, em Python 3 com biblioteca padrão e SQLite: agenda de consultas (primeira consulta e retornos, presencial ou online com link informado pela equipe), confirmação automática, lista de espera, retorno programado, **plano alimentar** registrado pelo nutricionista e consultado pelo paciente na conversa, **diário** (água, refeições feitas/puladas, peso, foto de refeição por metadados) com lembretes opt-in e metas, FAQ, fila humana no Telegram, sinais de alerta, campanhas com trava mínima de publicidade, LGPD de dado de saúde, cadastros, backup e exportação mensal para o Painel de Recuperação do **Raio-X de Margem** (pacote `clinica`). Base: o `atende-clinica`, adaptado.

**Estado (19/10/2026): implementação em andamento.** Base HTTP/SQLite, autenticação e agenda presencial/online implementadas; 19 dos 99 testes passam. Conversa, plano alimentar, diário, integrações, páginas e entrega Docker continuam pendentes. Estado detalhado em `longrun/2026-10-05-nutri-v1/state.md`.

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

- Linux/macOS com `git`, `python3` ≥ 3.10 e `pytest` (`pip install pytest`; é ferramenta de desenvolvimento, a aplicação não depende dela).
- Um agente pela **assinatura**: Codex CLI (`codex`) ou Claude Code (`claude`). Nenhuma API é chamada.
- Para a verificação independente final: `docker`.
- Método e ferramentas de execução longa: clone de `~/projetos/execucao-longa` (`tools/loop-longrun.sh`, `docs/PLANO-EXECUCAO-LONGA.md`). Se não tiver, a rota `/goal` interativa (abaixo) não precisa dele.

### 1. Responder as decisões e congelar o contrato

```sh
cd atende-nutricao
# leia docs/DECISOES-ABERTAS.md; "ok em tudo" = nada a mudar
python3 -m pytest -q --collect-only | tail -n 1     # 99 tests collected
bash longrun/2026-10-05-nutri-v1/congelar.sh        # grava hash-congelado.txt e faz 1 commit
```

Se mudar algo marcado ⚠ nas decisões, edite `docs/ESPECIFICACAO.md` e os testes **antes** de congelar. Depois de congelado, contrato e testes são protegidos: o agente não os altera; se um teste contradizer a spec, ele registra em `failures.md` e para (portão humano).

### 2a. Loop headless (Codex `gpt-6-astra`)

```sh
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-nutri-v1
```

Configuração em `longrun/2026-10-05-nutri-v1/loop.env` (teste rápido/final, arquivos protegidos, 20 ciclos × 30 min, 8 GB, parada após 3 ciclos sem avanço, `CODEX_ARGS` liberando socket local no sandbox). O loop faz `flock`, `timeout`, `MemoryMax`, reverte ciclo que mexer em arquivo protegido, commita checkpoint por ciclo e para sozinho quando o teste final passa.

### 2b. `/goal` no Codex TUI

```sh
codex -c sandbox_workspace_write.network_access=true
```

Cole o conteúdo de `longrun/2026-10-05-nutri-v1/prompt-goal-codex.md`. Acompanhe com `/goals`; pause/retome com `/goal pause|resume`.

### 2c. `/goal` no Claude Code

Abra uma sessão nova na pasta do projeto e siga `longrun/2026-10-05-nutri-v1/prompt-goal-claude.md` (a condição do `/goal` + o mesmo bloco do Codex como primeira mensagem).

### 3. Acompanhar

```sh
tail -n 20 longrun/2026-10-05-nutri-v1/loop.log        # headless
cat longrun/2026-10-05-nutri-v1/state.md               # Funciona / Falta / Como retomar
tail -n 5 longrun/2026-10-05-nutri-v1/progress.md
python3 -m pytest -q tests/ | tail -n 3
```

Pronto = `python3 -m pytest -q tests/` → **99 passed** e `bash longrun/2026-10-05-nutri-v1/verificar-limites.sh` → **LIMITES OK** (hash do contrato intacto, nº de testes igual, `hash-congelado.txt` igual ao gravado pelo commit de congelamento, só arquivos do escopo, sem dependência externa, sem URL externa, sem chave, sem download de mídia, sem `0.0.0.0` no código).

### 4. Verificação independente (nível 4, humano)

```sh
python3 longrun/2026-10-05-nutri-v1/verificar-independente.py   # INDEPENDENTE OK
```

Procura valores do fixture copiados no código, sobe um consultório nunca visto (passo de 20 min, consulta de 40 min, retorno em 15 dias, sem atendimento online, plano com refeições de outros nomes, outro relógio) e confere regras que só passam se a lógica for geral — agenda, chat, plano, peso, água, refeição, lembrete, retorno, trava de campanha, concorrência, Raio-X, LGPD —; depois faz `docker build` e testa o healthcheck do container. Abra `/` e `/equipe` no navegador.

## Executar (depois de implementado)

```sh
mkdir -p dados && cp exemplos/nutricao.json dados/nutricao.json   # troque TROQUE-ESTE-TOKEN
./atende serve --porta 8080 --dados dados
```

O chat do paciente fica em `/`, a página da equipe em `/equipe` (header `X-Token`). `ATENDE_AGORA` fixa o relógio só para testes. A seção de deploy (compose, proxy HTTPS, webhooks da Evolution e do Telegram, backup diário) é escrita pelo implementador conforme a seção 21 da especificação.

## Arquivos

- `docs/ESPECIFICACAO.md` — contrato (21 seções, tabela de rotas, regras com fronteiras, fora do v1).
- `docs/DECISOES-ABERTAS.md` — decisões com proposta padrão; perguntas para o dono (inclusive o ⚠ do CFN).
- `docs/MAPA-RAIO-X.md` — cada vazamento do pacote `clinica` → peça do v1 ou motivo de ficar fora.
- `docs/VALIDACAO.md` — validação adversarial do plano (05/10/2026): checklist teste × spec, contas conferidas, saída dos checks de trava/harness.
- `tests/` — 99 testes caixa-preta (`conftest.py` sobe o CLI, relógio fixo, servidor falso de Evolution/Telegram). Fixture em `tests/fixtures/nutricao.json`; cópia em `exemplos/`.
- `longrun/2026-10-05-nutri-v1/` — goal (nível 3+), plan, state, canal, loop.env, prompts, `congelar.sh`, `verificar-limites.sh`, `verificar-independente.py`.
- `FALHAS.md` — uma linha por falha (data, o que quebrou, menor correção, prompt | infra).
