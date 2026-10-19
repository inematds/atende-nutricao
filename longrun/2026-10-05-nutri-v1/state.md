# Estado — atualizado 2026-10-19 13:58

## Funciona
- Base Python 3/biblioteca padrão, HTTP com threads, SQLite transacional em --dados, semente única, auth e agenda presencial/online. Versão 0.2.0.
- Conversa persistente: normalização preservando decimais, prioridade emergência/alerta, parar e parar lembretes, fila humana única por telefone, silêncio enquanto aberta, encerramento/resposta pela API, FAQ e agendamento com nome/serviço/horário/modalidade; opções inválidas repetem e conflito oferece novos horários.
- Confirmações idempotentes, respostas exatas às pendências, cancelamento dispara espera para o mesmo horário/profissional, retorno por presença e caixa de saída simulada. Remarcação renova a confirmação.
- Planos versionados pela equipe, leitura por refeição ou plano completo, envio simulado, dúvida fora do plano encaminhada ao humano. Não há prescrição automática.
- Diário de água/refeições/peso, série de pesos com ROUND_HALF_UP e resposta neutra, metas e lembretes com tolerância/unicidade; exportação GET /pacientes/id/dados com histórico da conversa e caixa de saída.
- Suíte completa final: **62 passed / 37 failed** em 76,24 s. **LIMITES OK** (hash 9529d2ce312095d9; 99 testes).
- Verificação local adicional: fluxo de agendamento retomado após reinício; parar antes de cadastro conservado; atendimento humano silencia FAQ e emergência eleva prioridade sem duplicar fila.

## Falta
- Campanhas e trava mínima; exclusão/anonimização LGPD; Raio-X HTTP/CLI.
- Edição/inativação dos cadastros, API de bloqueios, backup/restauração. Agenda já usa horários próprios/bloqueios, mas falta edição dessas coleções.
- Evolution (texto/foto por metadados, envio e retry) e Telegram (avisos, encaminhamento e comandos), sempre com servidores falsos nos testes. Caixa de saída atual só simula e reenviadas é zero.
- Dockerfile/compose/env, seção Deploy na VPS e páginas chat/equipe. README preservado, apenas linha de estado atualizada.
- A leitura /dados existe; DELETE do paciente ainda não existe. Foto só será inserida pelo webhook quando implementado.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Especificação inteira e conftest foram lidos neste ciclo.
2. Código: storage.py persiste documentos; domain.py agenda/roteamento; conversation.py prioridades/fluxo; tasks.py caixa de saída/tarefas; nutrition.py planos/metas/diário/exportação.
3. Próxima ação: campanhas, LGPD e Raio-X; depois cadastros/bloqueios/backup e integrações. Não reimplementar o que já passa.
4. Rodar `python3 -m pytest -q tests/ > /tmp/atende-nutricao-pytest-final.log 2>&1` e ler somente `tail -n 30`.
5. Rodar `bash longrun/2026-10-05-nutri-v1/verificar-limites.sh` e atualizar os registros.

Não marcar concluído: 37 testes ainda falham. Nenhum arquivo protegido alterado; nenhum commit ou acesso externo.
