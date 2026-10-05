# CLAUDE.md — atende-nutricao

Sistema de atendimento ao paciente para um consultório de nutrição: agenda (presencial/online), confirmação, lista de espera, retorno, plano alimentar, diário (água, refeições, peso, foto por metadados) com lembretes e metas, FAQ, fila humana, sinais de alerta, campanhas com trava mínima, LGPD de dado de saúde, WhatsApp pela Evolution, equipe pelo Telegram e exportação para o Painel do Raio-X de Margem (pacote `clinica`).

- Repo local (sem remoto ainda). Autor de commit: `inematds <inematds@gmail.com>` (config local).
- **Contrato:** `docs/ESPECIFICACAO.md`. Testes caixa-preta em `tests/` (pytest sobe `./atende serve --porta 0`). Contrato e testes são **protegidos** durante a execução longa — só humano altera, e aí recongela o hash (`longrun/.../congelar.sh`).
- Decisões pendentes: `docs/DECISOES-ABERTAS.md` (⚠ trava do CFN é mínimo comum: o dono confirma antes de publicar campanha). Relação com o Raio-X: `docs/MAPA-RAIO-X.md`.
- Execução longa: `longrun/2026-10-05-nutri-v1/` (método em `~/projetos/execucao-longa`). Como rodar: `README.md`, seção "Como rodar no seu ambiente".
- `python3` (não existe `python` neste host). Sem dependência externa no v1 (biblioteca padrão + SQLite).
- Nenhuma API (WhatsApp/Meta, LLM pago, análise de imagem, Pix/PSP, OpenRouter, Groq) sem autorização explícita. Sem rede externa no código; nunca baixar mídia do WhatsApp (foto = só `mimetype`/`caption`).
- O bot **nunca prescreve**: só plano do paciente + FAQ; peso registrado sem comentário (lista de palavras proibidas na seção 10 da spec).
- Servidor de teste: só `127.0.0.1`, porta 0; matar só o PID que subiu (nunca `pkill -f`).
- Versão em `VERSION` (semver do CLAUDE global: minor carrega o patch).

## Self-learning

When I correct you, or you catch yourself making a mistake: before continuing, add the lesson as a one-line rule under ## Lessons, so it never happens again.

## Lessons
- `congelar.sh` grava `BASE = HEAD` antes do commit de congelamento: `BASE` é o **pai** do commit "contrato congelado", não ele. Toda guarda sobre o congelamento compara com `git show <commit-congelamento>:hash-congelado.txt` e `<commit>^`, e se prova num clone antes de valer. (05/10/2026)
