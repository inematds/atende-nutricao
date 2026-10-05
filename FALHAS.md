# FALHAS

| data | o que quebrou | menor correção | prompt \| infra |
|---|---|---|---|
| 2026-10-05 | revisão: `test_publico_so_com_consentimento_e_sem_parar` exigia 422 para `{"texto": "   "}` e a spec só previa 422 com `violacoes` (implementador honesto falharia) | linha de `/api/campanhas` na §5: "texto ausente, vazio ou só espaços → 422" | prompt |
| 2026-10-05 | revisão: dois testes do diário deixavam 2–3 `atende serve` vivos ao mesmo tempo no mesmo `--dados` (a spec só promete reinício, não acesso simultâneo ao SQLite → "database is locked" possível) | `s.parar()` antes de subir o próximo servidor | prompt |
| 2026-10-05 | planejamento: guarda nova do `verificar-limites.sh` exigia que `BASE` fosse o commit "contrato congelado", mas `congelar.sh` grava `BASE = HEAD` **antes** de commitar (BASE é o pai desse commit) → `LIMITES OK` nunca saía no clone de teste | checar que `hash-congelado.txt` da árvore é igual ao do último commit de congelamento e que `BASE` é o pai dele (provado no clone: stub honesto OK, `BASE` forjado → violação) | prompt |
