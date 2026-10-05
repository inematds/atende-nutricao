# Validação adversarial do plano — 05/10/2026

Feita por um agente que **não viu** o planejamento, contra o briefing de validação (10 itens) e o adendo de saúde/movimento. Resultado: **1 problema que bloquearia a execução, 6 que atrapalhariam, 3 cosméticos — todos corrigidos**; 99 testes (contagem inalterada; uma asserção nova dentro de um teste existente). Checks 6, 7 e 10 reexecutados num clone temporário (saída no fim). Cada correção tem uma linha em `FALHAS.md`.

## Checklist

| # | Item | Resultado |
|---|---|---|
| 1 | Teste × especificação, item a item | **Corrigido.** 99 testes lidos contra as 21 seções. 1 contradição real: `test_refeicao_sem_nome_usa_horario_e_exige_plano` subia o 3º servidor em 06/10 06:00 e esperava esse registro **por último**, mas a §10 ordena o diário por `quando` → o implementador honesto reprovava; o servidor passou para 07/10 06:00 (mesmo cenário) e o teste agora afirma a ordem por `quando`. 4 pontos em que o teste exigia o que a spec não escrevia, agora escritos sem mudar o que os testes pedem: oferta da lista de espera é do **mesmo horário e profissional** (`test_espera_horario_ja_ocupado` exige `ocupado` com o Dr. Marcos livre); `/api/horarios` com profissional existente que não faz o serviço → 200 `[]`; `/dados.mensagens` tem `saida` = respostas do bot na conversa (o teste não cria mensagem da caixa de saída); a resposta ao nome do paciente novo já lista os serviços. Cosméticos: `docker-compose.yml` com o literal `127.0.0.1:8080:8080` (o teste exige o literal); ordem "depois `profissional`" em `/api/horarios` definida (cadastro); `cadastro` vem antes de `nutricionista` para telefone desconhecido. Conferido também: ordem de cada listagem (saída, fila, pacientes, profissionais, FAQ, bloqueios, planos, diário, pesos, agendamentos), pontas (`[inicio, fim)`, `agora < inicio <= agora + 48h`, `T <= agora <= T + tol`, `(origem, data + 30]`, `20 <= peso <= 400`), arredondamentos (1 casa: adesão, variação, Raio-X, peso), códigos 400/401/404/409/422, textos literais (`192`/`pronto-socorro`, `188`/`nutricionista`, `entre 20 e 400`, `Por enquanto só consigo ler…`, `Novo agendamento:`/`Cancelado:`, formato do plano e das linhas do `/agenda`), contagem exata de mensagens só onde a spec limita (1 por agendamento/lembrete/campanha, FAQ "só ela"). |
| 2 | Valores esperados recalculados (python3) | **OK** — todas as contas batem (lista abaixo). |
| 3 | Contradições internas / estado entre testes / fixture | **OK** (após o item 1). Cada teste usa `tmp_path` próprio; nenhum depende de outro. A fixture comporta todo cenário usado: 06/10 ter 09:00 com antecedência 2 h → 11:00; 07/10 qua, 08/10 qui, 09/10 sex, 13/10 ter válidos; 05/09 sáb 09:00 (08–12) e 08/09 ter válidos para o `montar_mes`; 12/10 feriado e 11/10 domingo vazios; só a Dra. Lia faz bioimpedância; Dr. Marcos livre às 07/10 09:00 no teste de espera (por isso a regra "mesmo profissional" precisava estar escrita). Sinais de alerta: as duas listas não colidem com as frases do diário usadas (`pulei o almoço`, `nao comi nada hoje`, `comi`, `2 copos`, `peso 82,5`, `tomei 1 copo`) nem com FAQ/plano/link; `vomitei de proposito depois do almoço` cai na regra 2 antes do diário (teste cobre). |
| 4 | Burlável? | **OK.** `verificar-independente.py` usa consultório nunca visto (passo 20, consulta 40 min, antecedência 1 h, retorno 15 dias, aviso 3 dias, tolerância 30 min, `atende_online: false`, outro feriado, outro token e relógio, plano "Desjejum/Refeição principal/Ceia leve", FAQ novo), tudo explícito (`api.req` reescrito, nenhum atalho do conftest), grep de 12 valores da fixture no código, `docker build` + healthcheck real; cobre grade (11 horários, 07:00–10:20), 409 com passo 20/duração 40, 422 online, lembrete fora da tolerância de 30 min, refeição por nome, dúvida fora do plano, peso neutro, faixa, água com meta, adesão, chat sem pergunta de modalidade, retorno em 15 dias, trava de campanha, concorrência, Raio-X de novembro e LGPD. Rota que ignora entrada cai na grade de 20 min, no feriado novo e no token novo. |
| 5 | Raio-X | **OK.** Os cinco ids existem em `~/projetos/raio-x-margem/setores/clinica.js` (`atendimentos_mes` l.29, `falta_pct` l.32, `ocupacao_pct` l.35, `clientes_novos_mes` l.38, `retorno_atual_pct` l.39). Formato `{tipo: "acompanhamento", pacote, cliente, base: {data, valores}, meses: [{mes, valores, obs}]}` é o do `app/painel-motor.js` (l.5–6); `linhaDoTempo` ordena por `mes`, então inserir/substituir o mês funciona. A redefinição de `retorno_atual_pct` (qualquer serviço realizado em `(data_origem, data + 30]`) está escrita na §12 e em `DECISOES` #12, com a armadilha anotada no `canal.md` (com `retorno_dias = 30` a origem cai exatamente em `data − 30` e não conta). |
| 6 | Travas (`loop.env`, `goal.md`, prompts, `congelar.sh`, `verificar-limites.sh`) | **OK + endurecido.** `CODEX_ARGS="-c sandbox_workspace_write.network_access=true"`; `PERMITIDOS="."`; `PROTEGIDOS` = `tests/ pytest.ini docs/` + goal, hash, congelar, verificar-*, loop.env, prompt.md; `goal.md` = 99 = coletados; prompts proíbem API real e os protegidos. **Guarda nova do congelamento provada no clone:** `congelar.sh` numa árvore real grava `BASE` = pai do commit "contrato congelado"; stub honesto → `LIMITES OK`; **3 commits de checkpoint** com a mensagem do `loop-longrun.sh` → continua `LIMITES OK`; `hash-congelado.txt` forjado na árvore → violação; `BASE` forjado → violação; recongelamento forjado num commit que também muda um teste → violação (guarda acrescentada: o commit de congelamento só pode tocar `hash-congelado.txt`; mais de um commit de congelamento imprime ATENÇÃO); teste alterado (working tree e commitado) → hash; `https://api.telegram.org`, `0.0.0.0`, arquivo fora do escopo e `getBase64FromMediaMessage` → violação. `goal.md` e os prompts agora também proíbem **rodar** `congelar.sh`. Saída abaixo. |
| 7 | Harness | **OK.** 99 coletados sem erro; sem implementação `15 failed, 84 errors`, **0 passed**; stub que imprime `PORTA=<n>` e responde `/api/saude` → `test_saude_traz_versao_do_arquivo` **1 passed** e nenhum processo vivo depois; `Externo` grava rota/headers/corpo/`message_id`, devolve 201 em `/message/*` e 200 no Telegram, e com `falhas=1` o 1º POST sai 500 e o 2º 201 (`whats()` só conta os 2xx). |
| 8 | Tamanho e fechamento | **OK.** 99 testes / 21 seções; mesmo molde do atende-clinica (93 em 7 de 20 ciclos), com mais regras de conversa (13 regras + diário/plano) — 20 ciclos × 30 min é folga razoável; "fora do v1" (§14) explícito. Nenhum teste usa rede real, Docker real (`test_docker` é estático; o build fica no nível 4 humano) nem relógio real (`ATENDE_AGORA` fixo em todo `Servidor`, `tarefas/rodar {agora}`); esperas são `esperar()` ≤ 5 s em servidor local e `sleep` de 0,5–0,8 s. |
| 9 | README "Como rodar no seu ambiente" | **OK.** Pré-requisitos, congelar, loop headless / `/goal` Codex / `/goal` Claude, acompanhar, verificação independente. Caminhos citados existem (`~/projetos/execucao-longa/tools/loop-longrun.sh`, `docs/PLANO-EXECUCAO-LONGA.md`, `prompt-goal-*.md`, `verificar-*.{sh,py}`). "Deploy na VPS" fica de fora de propósito (o teste do README falha até implementar) e o `prompt.md`/`goal.md` mandam acrescentá-la sem remover "Como rodar". Linha de `docs/VALIDACAO.md` acrescentada em "Arquivos". |
| 10 | Vazamento de processo | **OK (já estava) e provado.** `conftest.py` tem `SERVIDORES` + fixture `autouse` que para todos no teardown. Prova no clone: teste temporário que sobe `Servidor(dados)` e `assert False` → `1 failed` → `pgrep -af "[c]lone-nutri/atende serve"` vazio. Contraprova: com `autouse=False` o mesmo teste deixa 1 órfão (encerrado por mim, só aquele PID). Stub, teste temporário e clone apagados. |

Dono decide (não derruba teste, registrado em `DECISOES-ABERTAS.md` #6): `parei de comer` e `laxante` casam por substring (ex.: "parei de comer doce" vira fila alta); `avc` também é substring (não achei palavra comum em português que o contenha). Lista de palavras não significativas do FAQ fica a critério do implementador: nenhum teste depende dela (as perguntas usadas casam ≥ 67 % ou 0 % com qualquer lista razoável).

## Contas conferidas (python3, independentes dos testes)

- **Dias da semana:** 06/10/2026 = terça (agora) · 07/10 qua · 08/10 qui · 09/10 sex · 10/10 sáb · 11/10 dom · 12/10 seg (feriado) · 13/10 ter · 05/09 sáb · 08/09 ter · 03/11 ter (verificador) · 02/11 seg (feriado do verificador) · 04/11 qua.
- **Grade 06/10 a partir de 11:00 (antecedência 2 h):** retorno 30 min → manhã 11:00, 11:30 + tarde 14:00–17:30 (8) = 10 × 2 profissionais = **20**, primeiros `(11:00, lia), (11:00, marcos), (11:30, lia)`; primeira 60 min → 11:00 + 14:00–17:00 (7) = 8 × 2 = **16**; bioimpedância 07/10 inteira (só Lia) → 8 + 8 = **16**, 08:00…17:30, sem 12:00; sábado 10/10 → 8 × 2 = **16**; Carla qua 13:00–15:00 → 13:00, 13:30, 14:00, 14:30; avaliação 90 → 08:00 cabe (09:30 ≤ 12:00); 120 → 10:00 cabe (12:00), 10:30 não.
- **Chat com 06/10 lotado:** 07/10 08:00 Lia, 08:00 Marcos, 08:30 Lia (dentro de 14 dias).
- **Confirmação (48 h):** 07/10 09:00 está a 24 h ✓; 09/10 09:00 a 72 h ✗; de 07/10 10:00, 09/10 09:00 fica a 47 h ✓.
- **Retorno:** 07/10 + 30 = **06/11** (sexta); aviso de 06/11 − 7 = **30/10** (29/10 = 0, 30/10 = 1, 31/10 = 0). Verificador: 03/11 + 15 = **18/11**; aviso a partir de 18/11 − 3 = **15/11** (14/11 = 0, 15/11 = 1).
- **Lembretes (tolerância 60):** 09:00 → janela [09:00, 10:00]: 09:00 ✓, 10:30 ✗; 15:00 → [15:00, 16:00]: 15:59 ✓, 16:01 ✗; 07/10 09:30 ✓ → 3 lembretes. Refeições: 07:30 → [07:30, 08:30] e 10:00 → [10:00, 11:00] não contêm 09:00 → 0; almoço 12:30 → [12:30, 13:30] contém 12:45 ✓ e 12:50 (já enviado) = 0. Verificador (tolerância 30): 06:00 ✓ às 06:00; 06:31 ✗.
- **Peso:** 82,5 → `82,5 kg`; 82 → `82,0 kg`; variação 80 − 82,5 = **−2,5**; último = maior `quando` (80 em 05/11); 500 → fora; **79.25 → 79,3** (`ROUND_HALF_UP`; `round(79.25, 1)` = 79.2). Verificador: 91,3 / 89,9 → variação **−1,4**; 15 → fora.
- **Água:** 2 + 1 = 3 copos; com meta 8: 3 + 1 = `4 de 8 copos`; diário 06/10 2 + 07/10 3 = 5. Adesão: 1 feita + 1 pulada = **50,0**; filtro 07/10 = 1/1 = **100,0**; 08/10 = **0**. Verificador: 0 feitas + 1 pulada = **0**.
- **Diário ordenado por `quando`:** 06/10 09:00 (2 registros, ids crescentes) < 06/10 13:00 < **07/10 06:00** — por isso o 3º servidor do teste sobe no dia 7.
- **Raio-X out/2026:** dias úteis sem o feriado 12/10 = 22 − 1 = **21** × 480 + **5** sábados (3, 10, 17, 24, 31) × 240 = 11 280 × 2 profissionais = **22 560 min**; ativos = 60 + 30 + 30 (falta) + 30 + 30 (agendado) + 30 = **210** (cancelado não conta) → 210/22 560 = 0,9309 → **0,9** (tolerância do teste 0,06); realizados 4 (p1 ×2, p3, p6); `falta_pct` 1/(4+1) = **20,0**; novos = p1 (07/10) e p3 (08/10) = **2** (p6 já realizou em 05/09); retornos com data em outubro: p6 05/09 + 30 = **05/10** (tem realizado em 07/10 ∈ (05/09, 04/11]) e p7 08/09 + 30 = **08/10** (não) → **50,0**. Setembro: 2 realizados, 2 novos, 0 faltas, nenhum retorno com data em setembro → 0. Após `DELETE` no `test_dados_e_exclusao`: só o realizado de 08/10 conta → 1. Verificador nov/2026: 1 realizado, 1 novo, retorno de 18/11 sem outro realizado → 0.
- **Acompanhamento:** mês 2026-10 = base `{falta_pct: 18, ticket_medio: 250, atendimentos_mes: 400}` mesclada com o medido → `ticket_medio 250`, `falta_pct 20.0`, `atendimentos_mes 4`; rodar 2× substitui (1 mês).
- **Telefones:** `(41) 99999-0001`, `+55 41 99999 0001`, `41999990001` → `+5541999990001`; `41 3333-4444` (10 dígitos) → `+554133334444`; `123`, `abc`, `+55 41 9999` (9), `4199999000112` (13 sem 55) → inválidos.

## Saída dos checks (clone temporário, 05/10/2026)

```
### 6.1 congelar.sh no clone
congelado: HASH=9529d2ce312095d9 TESTES=99
HASH=9529d2ce312095d9
BASE=f3c341081a0d84dbfeb8f57b424f2cdbff0da195
TESTES=99
### 6.2 sem implementação → deve acusar
LIMITE VIOLADO: não há implementação (atende/src/web)
### 6.3 stub honesto
LIMITES OK (hash 9529d2ce312095d9, 99 testes, escopo ok, sem API/rede)
### 6.4 três commits de checkpoint (mensagem do loop-longrun.sh) → continua OK
594db18 longrun nutri-v1: checkpoint ciclo 3
a9bbb0c longrun nutri-v1: checkpoint ciclo 2
29bedcb longrun nutri-v1: checkpoint ciclo 1
d8ec2da longrun nutri-v1: contrato congelado (9529d2ce312095d9, 99 testes)
LIMITES OK (hash 9529d2ce312095d9, 99 testes, escopo ok, sem API/rede)
### 6.5 hash-congelado.txt forjado na árvore
LIMITE VIOLADO: hash do contrato mudou (9529d2ce312095d9 ≠ 0000000000000000)
### 6.6 BASE forjado (= HEAD)
LIMITE VIOLADO: hash-congelado.txt difere do gravado pelo congelamento (d8ec2da…)
### 6.7 recongelamento forjado num commit que também muda um teste
LIMITE VIOLADO: commit de congelamento (aae12c5…) altera mais do que longrun/2026-10-05-nutri-v1/hash-congelado.txt
### 6.8 teste alterado no working tree
LIMITE VIOLADO: hash do contrato mudou (85e347e5386afdc8 ≠ 9529d2ce312095d9)
### 6.9 teste alterado e commitado
LIMITE VIOLADO: hash do contrato mudou (85e347e5386afdc8 ≠ 9529d2ce312095d9)
### 6.10 URL externa / credencial no código
src/x.py:9:TG = "https://api.telegram.org"
LIMITE VIOLADO: chave/credencial ou API externa no código ou na entrega
### 6.11 bind 0.0.0.0 no código
LIMITE VIOLADO: bind em 0.0.0.0 no código (só o comando do container pode passar --host)
### 6.12 arquivo fora do escopo
LIMITE VIOLADO: arquivos fora do escopo: tools.txt
### 6.13 download de mídia no código
LIMITE VIOLADO: download de mídia do WhatsApp no código (seção 19: só metadados)
### 6.14 estado final limpo
LIMITES OK (hash 9529d2ce312095d9, 99 testes, escopo ok, sem API/rede)
### 7.1 stub do CLI passa o teste de saúde
1 passed in 0.05s
### 7.2 processo encerrado?
nenhum atende serve do clone vivo
### 7.3 Externo falso registra pedidos e injeta 500
1º POST: 500
2º POST: 201
3º POST (telegram): 200
pedidos: [('/message/sendText/nutricao', 500, 'chave-evo', None), ('/message/sendText/nutricao', 200, 'chave-evo', 1001), ('/botTOKEN123/sendMessage', 200, 'chave-evo', 1002)]
whats() ok: 1 | whats(ok=False): 2 | telegram(): 1
### 10.1 teste que falha de propósito depois de subir o servidor (conftest atual)
1 failed in 0.06s
nenhum atende serve do clone vivo (teardown autouse funcionou)
### 10.2 contraprova: sem a fixture autouse o processo fica órfão
1 failed in 0.07s
órfãos sem autouse: 4137318
limpo: nenhum atende serve do clone vivo
### fim: apagando o clone
nenhum processo do clone
```

No repo real (não congelado de propósito — quem congela é o dono): `python3 -m pytest -q --collect-only | tail -1` → `99 tests collected`; `python3 -m pytest -q | tail -1` → `15 failed, 84 errors` (0 passed); `bash longrun/2026-10-05-nutri-v1/verificar-limites.sh` → `LIMITE VIOLADO: contrato não congelado (rode …/congelar.sh)`.
