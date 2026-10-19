# Falhas (só acrescentar; ao fim, a menor correção vira linha no FALHAS.md do projeto)

| data | o que quebrou | tentativa | resultado | prompt \| infra |
|---|---|---|---|---|
| 2026-10-19 13:51 | Suíte inicial: 80 testes falham por funções ainda ausentes (conversa, plano, /dados, tarefas, integrações, entrega e páginas) | Implementadas base e agenda; executada suíte inteira | 19 passed / 80 failed; nenhum conflito teste/spec identificado | infra (implementação incompleta) |
| 2026-10-19 13:58 | Suíte com funcionalidades pendentes (campanhas, exclusão LGPD, Raio-X, cadastros/bloqueios/backup, integrações, páginas e Docker) | Implementados conversa/tarefas/nutrição, com suíte inteira repetida após ajuste de tokens | 62 passed / 37 failed; nenhum conflito teste/spec identificado | infra (implementação incompleta) |
| 2026-10-19 14:04 | Restam cadastros/bloqueios/backup, páginas, integrações e Docker | Implementados campanhas/LGPD/Raio-X e executada suíte inteira | 70 passed / 29 failed; nenhum conflito teste/spec identificado | infra (implementação incompleta) |
