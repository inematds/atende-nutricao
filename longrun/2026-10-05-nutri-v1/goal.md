# Goal — nutri-v1

- **Início:** (preencher ao iniciar) · **Agente:** `codex exec` (gpt-6-astra, assinatura) em loop headless — `tools/loop-longrun.sh` · alternativa: `/goal` no Codex TUI ou no Claude Code
- **Tetos:** 20 ciclos × 30 min (≤ 10 h) · memória 8G por ciclo · estagnação 3 ciclos

## Resultado
`./atende` sobe um sistema de atendimento ao paciente para um consultório de nutrição — agenda de consultas (presencial ou online com link da equipe), confirmação, lista de espera, retorno programado, plano alimentar registrado pelo nutricionista e consultado pelo paciente na conversa, diário (água, refeições, peso, foto por metadados) com lembretes opt-in e metas, FAQ, fila humana, sinais de alerta, campanhas com trava mínima de publicidade e LGPD de dado de saúde, cadastros, bloqueios, backup, WhatsApp pela Evolution API, equipe pelo Telegram, exportação para o Painel do Raio-X (pacote `clinica`) e entrega em Docker para VPS —, conforme `docs/ESPECIFICACAO.md`.

## Especificação
**`docs/ESPECIFICACAO.md`** (contrato completo, congelado). Contexto: `docs/MAPA-RAIO-X.md`. Fora do escopo: seção 14 da especificação.

## Critérios de pronto (verificáveis)

**Função**
- [ ] `python3 -m pytest -q tests/` → **99 passed**, 0 failed, 0 errors, 0 skipped

**Regressão**
- [ ] a mesma suíte inteira no teste final (o loop só fecha se todas passam juntas; teste que passava e voltou a falhar impede o fecho)
- [ ] `./atende serve` reiniciado com o mesmo `--dados` mantém o estado (coberto por `test_estado_persiste_ao_reiniciar`, `test_confirmacao_sobrevive_a_reinicio`, `test_semente_so_na_primeira_vez` e `test_diario_resumo_e_filtro_por_dia`)

**Limite**
- [ ] `bash longrun/2026-10-05-nutri-v1/verificar-limites.sh` → `LIMITES OK` (hash do contrato = `hash-congelado.txt`, nº de testes coletados igual, `hash-congelado.txt` igual ao gravado pelo commit de congelamento, só arquivos do escopo — `atende`, `src/`, `web/`, `exemplos/`, `README.md`, `VERSION`, `Dockerfile`, `docker-compose.yml`, `.env.exemplo`, `.dockerignore`, `.gitignore`, `CLAUDE.md`, `FALHAS.md`, esta pasta —, sem SDK/dependência externa, sem URL externa, sem chave de API, sem `0.0.0.0` no código)

**Teste rápido por ciclo**: `python3 -m pytest -q tests/`
**Teste completo no final**: `python3 -m pytest -q tests/ && bash longrun/2026-10-05-nutri-v1/verificar-limites.sh`

**Depois do "concluído" (humano, nível 4):** `python3 longrun/2026-10-05-nutri-v1/verificar-independente.py` → `INDEPENDENTE OK` (sem valores do fixture no código + consultório nunca visto, com passo de 20 min, consulta de 40 min, retorno em 15 dias, sem atendimento online, plano com refeições de outros nomes, trava de campanha, peso e água + `docker build` e healthcheck do container) e abrir `/` e `/equipe` no navegador.

## Restrições
- só pela assinatura; nenhuma API, nenhuma rede externa, nenhuma dependência fora da biblioteca padrão do Python (decisão 2 de `docs/DECISOES-ABERTAS.md`)
- não mexer em: `tests/`, `pytest.ini`, `docs/` (inclusive `ESPECIFICACAO.md`), `goal.md`, `hash-congelado.txt`, `congelar.sh`, `verificar-*.{sh,py}`, `loop.env`, `prompt.md` (o hash congelado cobre `tests/`, `pytest.ini`, a spec e os dois verificadores); **nem rodar `congelar.sh`** (só o humano congela ou recongela — o `verificar-limites.sh` avisa se houver mais de um commit de congelamento)
- `README.md`: acrescentar "Deploy na VPS" sem remover "Como rodar no seu ambiente" (o teste do README exige as duas)
- servidor só em `127.0.0.1`; ao testar à mão, porta 0 e matar só o PID que subiu
- nunca baixar mídia do WhatsApp nem buscar URL vinda de payload: a foto vira registro só com metadados (seção 19); o nome do endpoint da Evolution de mídia em base64 e `downloadMedia` não podem aparecer no código nem em comentário (o `verificar-limites.sh` grepa)
- no loop headless não fazer commit (o loop faz); no /goal interativo, commit local a cada checkpoint; nunca criar repo remoto nem fazer push

## Portões humanos (parar e perguntar)
- teste que contradiz a especificação (registrar em `failures.md` com o trecho exato e parar — não "ajustar" o teste)
- qualquer chamada a API real (Evolution, Telegram, LLM, Pix, análise de imagem) — durante a execução só os servidores falsos locais dos testes; dependência externa
- deploy na VPS (é do humano, com as credenciais dele)
- mudança de contrato, criar repo, push, publicar
