# Estado — atualizado 2026-10-19 14:19

## Funciona
- Python 3/biblioteca padrão, HTTP com threads, SQLite transacional em --dados, semente única, auth e agenda presencial/online. Versão 0.6.0.
- Conversa persistente: normalização de decimais, prioridades emergência/alerta, parar/lembretes, fila humana única com silêncio enquanto aberta, respostas/encerramento pela API, FAQ e agendamento com modalidade; conflito oferece novos horários.
- Confirmações idempotentes, pendências exatas, espera no mesmo horário/profissional, retorno por presença, caixa de saída simulada; remarcação renova confirmação.
- Planos versionados, consulta por refeição/completo, envio simulado e dúvida encaminhada ao humano; sem prescrição automática.
- Diário de água/refeições/peso, ROUND_HALF_UP e resposta neutra; metas/lembretes com tolerância e unicidade; exportação /dados com histórico completo.
- Campanhas com validação antes do envio/consentimento; LGPD com anonimização e remoção de dados de saúde; Raio-X HTTP/CLI com merge idempotente.
- Cadastros: criação/edição/inativação de profissionais e serviços, edição de pacientes com telefone único, criação/exclusão de FAQ com efeito imediato. Horários por profissional, bloqueios com conflitos sem cancelamento automático e exclusão que libera horários.
- Backup consistente pelo SQLite com servidor ativo; restauração atômica com servidor parado. Teste de backup preservou paciente, agenda e plano após reinício.
- Suíte completa: **94 passed / 5 failed** em 20,68 s (reexecução final). **LIMITES OK** (hash 9529d2ce312095d9; 99 testes).
- Verificação local adicional: horário próprio vazio não herda o geral; edição inválida preserva cadastro; backup inválido não substitui banco; restauração em diretório novo funciona.

- Evolution implementada em src/integrations.py: webhook com segredo próprio, deduplicação persistente, conversa compartilhada, texto estendido e foto só por metadados; saída síncrona com status e reenvio de pendentes.
- Verificação local adicional deste ciclo: texto estendido e peso decimal; deduplicação após reinício; foto duplicada vira um registro; nenhum endereço de mídia ou thumbnail armazenado; histórico sem duplicação.

- Telegram em src/telegram.py: abertura com prioridade/última mensagem, encaminhamento em resposta, referências persistidas, resposta da equipe e comandos /responder, /encerrar, /fila, /alertas e /agenda. Avisos de agendamento/cancelamento pelo chat. Webhook com segredo próprio e filtro de grupo.
- Verificação adicional local: referências após reinício e resposta ao encaminhamento; update duplicado não reenvia; exclusão LGPD remove referências; falha HTTP no envio não impede abertura da fila.

## Falta
- Dockerfile, compose, .env.exemplo e seção Deploy na VPS preservando o README existente.
- Páginas chat/equipe em web/; ainda retornam 404.
- Não marcar concluído: restam 5 testes falhando, todos nas áreas acima. Nenhum conflito teste/spec identificado.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Especificação inteira e conftest lidos neste ciclo.
2. storage.py persiste documentos; domain.py agenda/roteamento; registrations.py cadastros/bloqueios; backup.py cópia/restauração; conversation.py fluxo/prioridades; tasks.py saída/tarefas; nutrition.py plano/diário/metas; reporting.py campanhas/LGPD/Raio-X; integrations.py Evolution; telegram.py equipe.
3. Próximo passo: Docker/README e depois páginas funcionais em web/, conforme seção 15. Não realizar deploy nem acessar rede externa.
4. Rodar suíte inteira com saída em arquivo e ler apenas tail -n 30. Log deste ciclo: /tmp/atende-nutricao-ciclo6-pytest.log.
5. Rodar verificar-limites.sh e atualizar registros. Não alterar arquivos protegidos nem fazer commit.
