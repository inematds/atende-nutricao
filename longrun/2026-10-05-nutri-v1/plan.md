# Plano (reescrever, não acumular)

## Estratégia atual
Contrato (`docs/ESPECIFICACAO.md`) e 99 testes caixa-preta prontos; nenhuma implementação ainda. Após `congelar.sh`, implementar em camadas, do que destrava mais testes para o que destrava menos, rodando a suíte a cada passo.

## Próximos passos
1. Base: `./atende serve` com `PORTA=<n>`, `--dados` (cria a pasta), cópia de `exemplos/nutricao.json`, SQLite com semente de profissionais/serviços/FAQ, `X-Token` antes de tudo, `Content-Type: application/json`, `/api/saude`, `/api/servicos`, páginas `/` e `/equipe` (destrava `test_basico`).
2. Agenda: grade, 422/409/404, concorrência (transação), modalidade/link, cancelar/remarcar/presença, listagens ordenadas, pacientes e telefone (destrava `test_agenda`); depois cadastros/bloqueios/backup (`test_cadastros`).
3. Conversa na ordem das 13 regras (normalização que preserva `,`/`.` entre dígitos; pendência só com texto igual), lembretes/espera/retorno, plano alimentar, diário/peso/metas, campanhas, LGPD, Raio-X, Evolution (texto e foto por metadados), Telegram, Docker/README.
