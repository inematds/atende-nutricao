# Estado — atualizado 2026-10-19 14:22

## Funciona
- Versão 0.7.0. Python 3/biblioteca padrão, servidor HTTP com threads, SQLite transacional em --dados, semente única e autenticação.
- Agenda presencial/online com link, horários por profissional, bloqueios, concorrência, confirmação, espera no mesmo horário/profissional e retorno por presença.
- Conversa persistente com prioridades, normalização decimal, pendências exatas, FAQ, fila humana e silêncio enquanto aberta; planos versionados e dúvidas encaminhadas.
- Diário água/refeições/peso/fotos por metadados, arredondamento neutro, metas/lembretes, campanhas com trava, LGPD e Raio-X HTTP/CLI.
- Cadastros, inativação, edição, backup SQLite consistente e restauração atômica com servidor parado.
- Evolution: texto/foto sem baixar mídia, deduplicação persistente, envio síncrono/retry. Telegram: avisos, referências persistidas, respostas/comandos, segredo e filtro de grupo.
- Dockerfile com Python oficial sem dependências, healthcheck urllib; Compose com porta só loopback, volumes dados/backups; .env.exemplo vazio e .dockerignore limitando contexto à aplicação.
- README preservado e acrescido de Deploy na VPS: configuração, proxy HTTPS, webhooks, tarefas e backup diário/restauração.
- Suíte deste ciclo: **98 passed / 1 failed** em 22,51 s. **LIMITES OK** (hash 9529d2ce312095d9; 99 testes).
- Checagem adicional local: servidor cria diretório de dados ausente, banco e configuração; comando do healthcheck executado contra porta efêmera retornou sucesso. Nenhuma integração externa chamada.

## Falta
- Implementar as páginas funcionais / e /equipe em web/, conforme seção 15. Único teste falhando: test_paginas (GET / retorna 404).
- Build e execução reais do container não realizados neste ciclo sem rede externa; verificação independente é etapa humana prevista no goal.
- Não marcar concluído enquanto a suíte inteira não passar junto com os limites.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. A especificação inteira e conftest foram lidos neste ciclo.
2. Implementar entrega HTML e JS em web/ e rotas no Handler de src/server.py; web/.gitkeep apenas mantém o diretório para COPY do Docker.
3. Reutilizar as rotas existentes de src/domain.py e módulos conversation/tasks/nutrition/reporting/registrations/integrations/telegram; nunca inserir dados da equipe no HTML público.
4. Rodar python3 -m pytest -q tests/ com log e tail -n 30; log deste ciclo: /tmp/atende-nutricao-ciclo7-pytest.log.
5. Rodar verificar-limites.sh e atualizar os registros. Não alterar arquivos protegidos, fazer commit, acessar rede externa ou realizar deploy.
