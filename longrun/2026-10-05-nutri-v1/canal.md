# Canal — nutri-v1 (só acrescentar; nunca reescrever)

Conhecimento do projeto que a compactação perde: fatos descobertos, aprendizados, glossário, armadilhas, onde estão as coisas.
Não é estado da tarefa (isso vai em state/plan/progress). Preencha cedo — o hook avisa na faixa 1 (~50% do contexto).

Formato: `- AAAA-MM-DD HH:MM · fato|aprendizado|glossário|armadilha · texto`

- 2026-10-05 16:30 · fato · Molde é o `~/projetos/atende-clinica` (93/93); o que muda está na seção 0 da spec. Config é `nutricao.json` (não `clinica.json`); relógio fixo por `ATENDE_AGORA`; o conftest limpa `EVOLUTION_*`, `TELEGRAM_*`, `WEBHOOK_*` e `ATENDE_*` do ambiente.
- 2026-10-05 16:30 · armadilha · Normalização da conversa preserva `,` e `.` entre dígitos (`82,5`); todo o resto da pontuação some. Regras novas (peso/água/refeição) casam por token inteiro, não por substring.
- 2026-10-05 16:30 · armadilha · Pendência de confirmação/espera só consome texto IGUAL a `1`/`sim`/`confirmo`/`2`/`cancelar`/`nao`; `nao comi` e `1 copo` seguem para o registro do diário (testes `test_responder_*`).
- 2026-10-05 16:30 · armadilha · `retorno_atual_pct` conta QUALQUER serviço realizado em `(data_origem, data + 30]` (pontas: origem exclusiva, fim inclusivo); com `retorno_dias = 30` o atendimento de origem cai exatamente em `data − 30` e NÃO pode contar.
- 2026-10-05 16:30 · armadilha · Lembrete de água/refeição só sai dentro de `[H, H + lembrete_tolerancia_min]`; fora disso o lembrete daquele dia nunca sai (não acumula). `enviadas` conta mensagens criadas mesmo com envio `pendente`; `nao_contatar` não cria mensagem.
- 2026-10-05 16:30 · armadilha · Foto do WhatsApp: só `mimetype`/`caption` viram registro; nunca chamar `getBase64FromMediaMessage` nem buscar a `url` do payload (o verificar-limites.sh acusa).
- 2026-10-05 19:00 · armadilha · (validação) Oferta da lista de espera é do MESMO horário e MESMO profissional liberados: o `1` não cai em outro profissional livre (§7). `/api/horarios` com profissional existente que não faz o serviço → 200 `[]`. `/dados.mensagens` inclui as respostas do bot na conversa como `saida`. Peso: `79.25` → `79,3 kg` (ROUND_HALF_UP, não `round()`). Diário ordenado por `quando`, depois `id` (um teste sobe servidor em 07/10 06:00 por isso).
- 2026-10-05 16:30 · fato · Os checks 2–4 do briefing exigem 0 passed sem implementação: Dockerfile, compose, `.env.exemplo` e a seção "Deploy na VPS" do README são do implementador; o README já traz "Como rodar no seu ambiente" e o teste exige as duas seções.
