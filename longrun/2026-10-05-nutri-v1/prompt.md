Você está num ciclo de uma execução longa no repo /home/nmaldaner/projetos/atende-nutricao.

RESULTADO: `./atende` (Python 3, só biblioteca padrão; código em `src/` e páginas em `web/`) implementa docs/ESPECIFICACAO.md por inteiro — atendimento de consultório de nutrição: agenda (presencial/online com link), confirmação, espera, retorno, plano alimentar, diário (água, refeições, peso, foto por metadados) com lembretes e metas, FAQ, fila humana, sinais de alerta, campanhas com trava mínima, LGPD, cadastros, backup, WhatsApp pela Evolution, equipe no Telegram, Raio-X e Docker.

ANTES DE AGIR: leia longrun/2026-10-05-nutri-v1/goal.md → state.md → plan.md → canal.md → últimas linhas de progress.md e failures.md. Na primeira vez, leia docs/ESPECIFICACAO.md inteiro e tests/conftest.py.

NESTE CICLO: escolha a próxima ação útil (comece pela base: `./atende serve` imprimindo `PORTA=<n>`, SQLite em --dados, semente de nutricao.json, auth; depois agenda (modalidade/link) → conversa (ordem das 13 regras da seção 6, normalização que preserva `,`/`.` entre dígitos, pendência só com texto igual) → lembretes/espera/retorno → plano alimentar → diário/peso/metas → campanhas → LGPD → raiox → cadastros/bloqueios/backup → Evolution (texto e foto por metadados) → Telegram → Docker/README → páginas), implemente, rode `python3 -m pytest -q tests/` (leva segundos). Leia só o fim da saída (`| tail -n 30`); saída longa vai para arquivo.

AO TERMINAR O CICLO (obrigatório):
- reescreva state.md (Funciona / Falta / Como retomar) e plan.md (próximos 3 passos);
- acrescente 1 linha em progress.md: data-hora, o que mudou, resultado do pytest (N passed / N failed);
- se algo deu errado, 1 linha em failures.md: erro → tentativa → resultado;
- decisões de design em decisions.md; fatos e armadilhas novos em canal.md (só acrescentar);
- quando `python3 -m pytest -q tests/` passar inteiro E `bash longrun/2026-10-05-nutri-v1/verificar-limites.sh` imprimir LIMITES OK, escreva "concluído" na primeira linha de "## Funciona" do state.md.

SE UM TESTE CONTRADIZ A ESPECIFICAÇÃO: não altere o teste nem a spec. Registre em failures.md (teste, trecho da spec, o conflito) e siga com os outros itens; isso é portão humano.

INTEGRAÇÕES: Evolution e Telegram só pelas variáveis de ambiente da spec; teste só contra o servidor falso dos testes. Nunca chame api.telegram.org nem uma Evolution real; nunca baixe mídia (a foto vira registro só com `mimetype`/`caption`/`message_id`) e não escreva o nome do endpoint da Evolution que devolve mídia em base64 nem em comentário (o verificar-limites.sh grepa esse nome e `downloadMedia`); nunca escreva URL externa no código.

BOT: nunca prescreve dieta, suplemento ou cálculo; responde só com o plano do paciente e o FAQ; peso registrado sem comentário de julgamento (lista de palavras proibidas na seção 10).

README: acrescente a seção "Deploy na VPS" (seção 21 da spec) SEM remover a seção "Como rodar no seu ambiente" nem a descrição do projeto; só atualize a linha de estado.

RESTRIÇÕES: não altere tests/, pytest.ini, docs/, goal.md, hash-congelado.txt, congelar.sh, verificar-*, loop.env, prompt.md. Só biblioteca padrão do Python 3 (`python3`, não `python`). Nenhuma API, nenhuma rede externa, nenhuma chave. Servidor só em 127.0.0.1. Não use `pkill -f`; mate só o PID que você subiu. Não faça commit (o loop externo faz).
