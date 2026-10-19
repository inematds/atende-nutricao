# Decisões (só acrescentar)

| data | decisão | motivo | alternativa descartada |
|---|---|---|---|

- 2026-10-19 13:51 · SQLite com documentos JSON por coleção/id e ordem por rowid; transação BEGIN IMMEDIATE antes de validar/reservar horário, evitando dupla reserva entre threads. Separação em storage/domain/server permite acrescentar módulos de conversa e tarefas.

- 2026-10-19 13:57 · Conversa, tarefas e nutrição em módulos próprios sobre a mesma transação SQLite. Fluxo, pendências respondidas, confirmações, retornos e marcadores de lembrete persistem no banco; respostas do bot e caixa de saída alimentam um histórico ordenado para /dados. Peso usa Decimal/ROUND_HALF_UP; somente a equipe escreve o plano.
