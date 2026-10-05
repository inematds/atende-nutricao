# Como o Raio-X de Margem alimenta este projeto

Fonte: `~/projetos/raio-x-margem` — pacote `setores/clinica.js` (herda de `setores/servicos.js`; nutrição = CNAE 8650-0/02 está no `cacador.cnaes` do pacote), receita `docs/modulos/servicos-agenda.md`, análise `docs/setores/servicos.md`, pesquisa `docs/setores/servicos-pesquisa-2026-10.md`. Números abaixo trazem a confiança que o próprio Raio-X dá (**oficial**, **imprensa**, **fornecedor**, **premissa**); número sem fonte lá é premissa aqui também.

## Vazamentos da clínica × o que o atende-nutricao ataca

| Vazamento (id no `clinica.js` / herdado de `servicos.js`) | Peça no v1 | Seção da spec |
|---|---|---|
| `faltas` — falta sem aviso (nº 1: consultório bem gerido 5–12 %, média ~25 % — fornecedor; lembrete por WhatsApp em 3 toques reduziu faltas ~19 % no SUS-CE — oficial, indireto) | confirmação automática 48 h com `1`/`2` (presencial e online com link) + lista de espera no cancelamento; `falta_pct` medido na agenda | 7, 8, 12 |
| `retorno` — paciente que não volta no prazo (`retorno_atual_pct`; na nutrição o acompanhamento é contínuo, `atendimentos_mes_recorrente` > 1) | retorno programado por serviço (`retorno_dias`), aviso `retorno_aviso_dias` antes; **plano alimentar + diário + lembretes** mantêm o paciente ligado ao consultório entre consultas; `retorno_atual_pct` conta qualquer serviço realizado depois da origem | 8, 9, 10, 12 |
| `ociosidade` — horário que nunca foi agendado (`ocupacao_pct`) | horários públicos + agendamento pelo chat (3 primeiros livres) + consulta **online** (ocupa horário sem deslocamento); `ocupacao_pct` medido | 3, 5, 6, 12 |
| `mao_de_obra` — recepção presa marcando e confirmando à mão (`horas_agenda_manual_semana`) | agendamento, confirmação, espera, retorno, FAQ, plano e registro do diário pelo bot; fila humana só para o que ele não resolve; `/agenda` e `/alertas` no Telegram | 6, 8, 20 |
| `plataforma` — plataforma de agendamento cobrando de quem já é seu (Doctoralia/BoaConsulta cobram mensalidade, não comissão — fornecedor) | canal próprio (chat web + WhatsApp do consultório); **fora** a comparação "o que paga × o que usa" (é da conversa do Raio-X, não do software) | 0, 19 |
| `orcamentos` — tratamento indicado que não começa (`aprovacao_atual_pct`) | **parcialmente**: `plano/enviar` + `enviado_em` registram que o plano chegou ao paciente, e o diário mostra adesão; a taxa de "plano apresentado × seguido" não é exportada (não é entrada medida pela agenda) | 9, 10 |
| `glosa` — glosa de convênio | **fora** — faturamento/TISS, não é atendimento | 14 |
| `pagamentos`, `antecipacao`, `caixa` — taxa de cartão, antecipação, juros | **fora** — negociação com adquirente e caixa, não é software | 14 |
| `marketing` — anúncio pagando por quem já é paciente | **fora** (sem integração com anúncios); a base consentida (`consentimento_marketing`, exportável por `/api/pacientes`) é o insumo; campanha só com consentimento e trava mínima | 11, 14 |
| sinal `fidelidade` / plano de cuidado contínuo | **fora** (precisa de PSP/Pix Automático = portão humano) | 14 |

## Regras que viraram trava testável

- **LGPD art. 11 (dado de saúde = sensível):** confirmação, retorno, lembrete e plano = tutela da saúde / pedido do próprio paciente (art. 11, II, f — interpretação do Raio-X, não texto da ANPD); campanha = consentimento específico e destacado (art. 11, I); legítimo interesse não serve (ANPD, exemplo 1). "PARAR" bloqueia tudo que é automático. Exportar e **apagar** plano/diário/pesos (art. 18). Foto de refeição: só metadados, nada de mídia.
- **Conselho (CFN):** ⚠ sem pesquisa no Raio-X. A trava de campanha (seção 11) usa só o mínimo comum a CFM/CFO/COFFITO — promessa de resultado e antes-e-depois — e **o dono confirma o CFN antes de publicar campanha** (`DECISOES-ABERTAS.md` #4). Nenhum artigo inventado.
- **Bot não inventa:** só plano do paciente + FAQ; `posso comer X` fora do plano → humano; fora do FAQ → "não entendi" → humano. Sinais de alerta → `192`/`188` + fila alta. Peso sem julgamento.

## Volta para o Raio-X

`GET /api/raiox?mes=` e `./atende raiox --acompanhamento` produzem em `valores` os ids de entrada do pacote `clinica` que a agenda mede — `atendimentos_mes`, `falta_pct`, `ocupacao_pct`, `clientes_novos_mes`, `retorno_atual_pct` — no formato do `app/painel-motor.js` (`{tipo: "acompanhamento", pacote, cliente, base: {data, valores}, meses: [{mes, valores, obs}]}`, `obs: "atende-nutricao"`). O que o sistema não mede (`ticket_medio`, `faturamento`, `horas_agenda_manual_semana`, `glosa_pct`…) fica como estava no acompanhamento. Adesão ao plano e série de peso ficam na página da equipe (não são entradas do Raio-X). Ciclo comercial: Raio-X mede o "antes" → atende-nutricao implanta a receita "Agenda cheia" (confirmação + espera + retorno) e segura o paciente entre consultas (plano + diário) → o painel mostra o "depois" todo mês, com número tirado da agenda real.
