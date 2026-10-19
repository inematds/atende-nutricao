# Decisões (só acrescentar)

| data | decisão | motivo | alternativa descartada |
|---|---|---|---|

- 2026-10-19 13:51 · SQLite com documentos JSON por coleção/id e ordem por rowid; transação BEGIN IMMEDIATE antes de validar/reservar horário, evitando dupla reserva entre threads. Separação em storage/domain/server permite acrescentar módulos de conversa e tarefas.

- 2026-10-19 13:57 · Conversa, tarefas e nutrição em módulos próprios sobre a mesma transação SQLite. Fluxo, pendências respondidas, confirmações, retornos e marcadores de lembrete persistem no banco; respostas do bot e caixa de saída alimentam um histórico ordenado para /dados. Peso usa Decimal/ROUND_HALF_UP; somente a equipe escreve o plano.

- 2026-10-19 14:03 · Reporting centraliza campanhas, LGPD e Raio-X sobre a transação existente. Anonimização mantém vínculo do histórico por paciente_id, remove telefone/texto e estado da conversa, preservando realizados/faltas e retornos para agregação. CLI mescla o mês anterior cronológico (ou base) e substitui o arquivo por rename.

- 2026-10-19 14:09 · Cadastros editados por lista explícita de campos; inativação preserva referências históricas. Backup usa sqlite3.Connection.backup para snapshot consistente com servidor ativo; valida origem somente leitura e substitui destino por arquivo temporário + rename. Restauração exige servidor parado; configuração nutricao.json permanece externa ao banco, conforme leitura no início.
