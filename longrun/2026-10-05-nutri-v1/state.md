# Estado — atualizado 2026-10-19 (ciclo 8, fechamento)

## Funciona
- Versão 0.8.0. Python 3/biblioteca padrão, servidor HTTP com threads, SQLite transacional em --dados, semente única e autenticação.
- Agenda presencial/online com link, horários por profissional, bloqueios, concorrência, confirmação, espera no mesmo horário/profissional e retorno por presença.
- Conversa persistente com prioridades, normalização decimal, pendências exatas, FAQ, fila humana e silêncio enquanto aberta; planos versionados e dúvidas encaminhadas.
- Diário água/refeições/peso/fotos por metadados, arredondamento neutro, metas/lembretes, campanhas com trava, LGPD e Raio-X HTTP/CLI.
- Cadastros, inativação, edição, backup SQLite consistente e restauração atômica com servidor parado.
- Evolution: texto/foto sem baixar mídia, deduplicação persistente, envio síncrono/retry. Telegram: avisos, referências persistidas, respostas/comandos, segredo e filtro de grupo.
- Dockerfile com Python oficial sem dependências, healthcheck urllib; Compose com porta só loopback, volumes dados/backups; .env.exemplo vazio e .dockerignore limitando contexto à aplicação.
- README preservado e acrescido de Deploy na VPS: configuração, proxy HTTPS, webhooks, tarefas e backup diário/restauração.
- Páginas / (chat do paciente) e /equipe (agenda, pacientes, plano, diário, peso, metas, fila humana, saída, FAQ) em web/, servidas por lista fechada no Handler com CSP; checagem de UI no navegador local (desktop/mobile) sem erros JS.
- Suíte final: **99 passed** (3 execuções seguidas). **LIMITES OK** (hash 9529d2ce312095d9; 99 testes).
- Checagem adicional local: servidor cria diretório de dados ausente, banco e configuração; comando do healthcheck executado contra porta efêmera retornou sucesso. Nenhuma integração externa chamada.

## Falta
- Nada dos critérios automáticos: 99/99, LIMITES OK, INDEPENDENTE OK (docker build + healthcheck do container incluídos).
- Humano: abrir / e /equipe no navegador; deploy na VPS com credenciais próprias; README.en.md/README.es.md ainda com o estado antigo (fora do escopo do verificar-limites).

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. A especificação inteira e conftest foram lidos neste ciclo.
2. Implementar entrega HTML e JS em web/ e rotas no Handler de src/server.py; web/.gitkeep apenas mantém o diretório para COPY do Docker.
3. Reutilizar as rotas existentes de src/domain.py e módulos conversation/tasks/nutrition/reporting/registrations/integrations/telegram; nunca inserir dados da equipe no HTML público.
4. Rodar python3 -m pytest -q tests/ com log e tail -n 30; log deste ciclo: /tmp/atende-nutricao-ciclo7-pytest.log.
5. Rodar verificar-limites.sh e atualizar os registros. Não alterar arquivos protegidos, fazer commit, acessar rede externa ou realizar deploy.
