# Progresso (só acrescentar)

| data/hora | checkpoint | commit | critério atingido? | tokens in/cached/out | compactações |
|---|---|---|---|---|---|
| 2026-10-19 13:51 | Base HTTP/SQLite/auth e agenda presencial/online implementadas; persistência manual OK; LIMITES OK | sem commit (loop externo) | pytest: 19 passed / 80 failed (34,72 s) | — | 0 |
| 2026-10-19 13:58 | Conversa/fila humana, confirmação/espera/retorno, planos, diário/peso/metas/lembretes e leitura /dados; v0.2.0; validação local extra OK; LIMITES OK | sem commit (loop externo) | pytest: 62 passed / 37 failed (76,24 s); +43 aprovados | — | 0 |
| 2026-10-19 14:04 | Campanhas, exclusão LGPD e Raio-X HTTP/CLI; v0.3.0; verificação adicional local OK; LIMITES OK | sem commit (loop externo) | pytest: 70 passed / 29 failed (76,08 s); +8 aprovados | — | 0 |
| 2026-10-19 14:09 | Cadastros, bloqueios e backup/restauração; v0.4.0; validação adicional local OK; LIMITES OK | sem commit (loop externo) | pytest: 79 passed / 20 failed (76,76 s); +9 aprovados | — | 0 |

| 2026-10-19 14:15 | Evolution: webhook texto/foto, deduplicação persistente, envio síncrono/retry; v0.5.0; validação adicional local OK; LIMITES OK | sem commit (loop externo) | pytest: 84 passed / 15 failed (67,37 s); +5 aprovados | — | 0 |

| 2026-10-19 14:19 | Telegram: avisos, encaminhamento, respostas, comandos, proteção e persistência; v0.6.0; verificação adicional local OK; LIMITES OK | sem commit (loop externo) | pytest: 94 passed / 5 failed; +10 aprovados | — | 0 |

| 2026-10-19 14:22 | Docker/Compose/env/contexto e Deploy na VPS; v0.7.0; inicialização sem dados + comando healthcheck OK; LIMITES OK | sem commit (loop externo) | pytest: 98 passed / 1 failed (22,51 s); +4 aprovados | — | 0 |
