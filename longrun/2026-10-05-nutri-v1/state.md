# Estado — atualizado 2026-10-19 13:51

## Funciona
- Base Python 3/biblioteca padrão: `./atende serve --porta 0 --dados DIR`, primeira linha `PORTA=<n>`, servidor com threads em loopback por padrão, criação da pasta e cópia de `exemplos/nutricao.json`.
- SQLite em `DIR/estado.sqlite3`: semente única de serviços, profissionais e FAQ; configuração relida ao iniciar. Cada operação HTTP usa transação `BEGIN IMMEDIATE`.
- Saúde/versão, serviços ativos ordenados, leitura de profissionais/FAQ, autenticação antes do corpo, respostas JSON e validação de JSON.
- Cadastro/listagem de pacientes, normalização e deduplicação de telefone. Agenda por janelas, duração, antecedência, feriados e profissional; conflito concorrente, cancelamento, remarcação, presença e modalidade/link.
- Suíte completa: **19 passed / 80 failed** em 34,72 s. Validador: **LIMITES OK** (hash 9529d2ce312095d9; 99 testes).
- Verificação local adicional: paciente e agendamento mantidos após reiniciar o servidor com o mesmo diretório (PERSISTENCIA BASE OK).

## Falta
- Conversa inteira (13 regras e fluxo persistente), confirmação/espera/retorno; presença ainda não cria retorno e cancelamento ainda não oferece espera.
- Plano alimentar, diário/peso/metas/lembretes, campanhas, LGPD (inclusive `/pacientes/{id}/dados`) e Raio-X.
- Edição/inativação dos cadastros, API de bloqueios, backup/restauração; regras da agenda já consultam bloqueios e horários próprios, mas não há API para editá-los.
- Evolution e Telegram (somente servidores falsos para testes), Docker/compose/env e seção Deploy na VPS; páginas web ainda não existem.
- Teste global de auth falha ao chegar à conversa pública, ainda não implementada; persistência global falha ao criar plano. Telefone duplicado funciona, mas seu teste falha na rota `/dados` pendente.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Especificação inteira e conftest já lidos neste ciclo.
2. Código: `src/storage.py` guarda documentos por coleção/id em SQLite; `src/domain.py` implementa agenda; `src/server.py` faz HTTP/auth/CLI.
3. Implementar conversa em módulo próprio, com estado persistido por telefone e prioridade das regras. Adicionar tarefas/espera/retorno depois.
4. `python3 -m pytest -q tests/ > /tmp/atende-nutricao-pytest.log 2>&1; tail -n 30 /tmp/atende-nutricao-pytest.log`
5. `bash longrun/2026-10-05-nutri-v1/verificar-limites.sh`

Não marcar concluído: 80 testes ainda falham. Nenhum arquivo protegido alterado; nenhum commit ou rede externa.
