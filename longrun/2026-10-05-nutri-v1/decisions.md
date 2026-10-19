# Decisões (só acrescentar)

| data | decisão | motivo | alternativa descartada |
|---|---|---|---|

- 2026-10-19 13:51 · SQLite com documentos JSON por coleção/id e ordem por rowid; transação BEGIN IMMEDIATE antes de validar/reservar horário, evitando dupla reserva entre threads. Separação em storage/domain/server permite acrescentar módulos de conversa e tarefas.

- 2026-10-19 13:57 · Conversa, tarefas e nutrição em módulos próprios sobre a mesma transação SQLite. Fluxo, pendências respondidas, confirmações, retornos e marcadores de lembrete persistem no banco; respostas do bot e caixa de saída alimentam um histórico ordenado para /dados. Peso usa Decimal/ROUND_HALF_UP; somente a equipe escreve o plano.

- 2026-10-19 14:03 · Reporting centraliza campanhas, LGPD e Raio-X sobre a transação existente. Anonimização mantém vínculo do histórico por paciente_id, remove telefone/texto e estado da conversa, preservando realizados/faltas e retornos para agregação. CLI mescla o mês anterior cronológico (ou base) e substitui o arquivo por rename.

- 2026-10-19 14:09 · Cadastros editados por lista explícita de campos; inativação preserva referências históricas. Backup usa sqlite3.Connection.backup para snapshot consistente com servidor ativo; valida origem somente leitura e substitui destino por arquivo temporário + rename. Restauração exige servidor parado; configuração nutricao.json permanece externa ao banco, conforme leitura no início.

- 2026-10-19 14:15 · Evolution reutiliza Conversation para texto e Nutrition.record para foto; só campos explícitos são persistidos. Transporte por urllib sem redirecionamento e timeout de 3 s, configuração somente no ambiente. Tasks.output tenta enviar sincronamente; tarefas reenvia somente pendências existentes no início da rodada. Deduplicação do webhook na mesma transação do estado.

- 2026-10-19 14:19 · Telegram usa transporte síncrono com timeout/sem redirecionamento e configurações somente no ambiente. Referências de abertura e encaminhamentos são persistidas; comandos reutilizam as mesmas rotas da equipe. Deduplicação por update_id evita reenvio da resposta humana. LGPD remove referências ao apagar atendimento, evitando associação indevida após reutilização de id.

- 2026-10-19 14:22 · Docker usa cópias explícitas e .dockerignore por lista permitida, excluindo dados, segredos, testes e logs do contexto. Bind geral só no comando do container; publicação Compose só loopback. Backups em volume separado; configuração e ambiente exigem cópia própria, pois backup CLI copia o banco.
