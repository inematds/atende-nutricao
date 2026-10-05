# Estado — atualizado 2026-10-05 (planejamento)

## Funciona
- Nada implementado ainda: não existe `./atende`, `src/` nem `web/`.
- Pronto: `docs/ESPECIFICACAO.md` (contrato, 21 seções), `tests/` (99 testes caixa-preta, `python3 -m pytest -q --collect-only` → 99 collected; `python3 -m pytest -q` → 0 passed), `tests/fixtures/nutricao.json`, `exemplos/nutricao.json`, `docs/DECISOES-ABERTAS.md`, `docs/MAPA-RAIO-X.md`, esta pasta (goal, loop.env, prompts, congelar, verificadores).

## Falta
- Humano: responder `docs/DECISOES-ABERTAS.md` (ou "ok em tudo"), rodar `congelar.sh` e iniciar o loop ou o `/goal`.
- Agente: toda a implementação (seções 1–21 da especificação), na ordem do `plan.md`.

## Como retomar (comandos exatos)
```
cd ~/projetos/atende-nutricao
python3 -m pytest -q tests/ | tail -n 3
bash longrun/2026-10-05-nutri-v1/verificar-limites.sh
```

Ao retomar/após compactação: ler goal.md → state.md → plan.md → canal.md → fim de progress.md e failures.md.
