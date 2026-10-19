"""Caixa de saída, ofertas de espera e tarefas idempotentes."""
from datetime import timedelta
from .domain import now, timestamp, required
from .storage import Error
from .integrations import send_whatsapp


class Tasks:
    def __init__(self, domain):
        self.d = domain

    def output(self, p, kind, text, instant=None, **extra):
        if not p['telefone'] or (p['nao_contatar'] and kind != 'humano'):
            return None
        message = self.d.save('saida', dict(tipo=kind, telefone=p['telefone'], paciente_id=p['id'], texto=text,
                            agendamento_id=None, status='simulado', quando=(instant or now()).isoformat(timespec='minutes'), **extra))
        self.d.save('mensagens', dict(telefone=p['telefone'], direcao='saida', texto=text, quando=message['quando']))
        message['status'] = send_whatsapp(p['telefone'], text)
        self.d.save('saida', message)
        return message

    def cancel(self, a):
        d = self.d
        if a['status'] == 'cancelado':
            raise Error(409, 'Já cancelado')
        a['status'] = 'cancelado'
        d.save('agendamentos', a)
        for request in d.all('espera'):
            if request['status'] != 'aguardando' or request['servico'] != a['servico'] or request['data'] != a['inicio'][:10]:
                continue
            p = d.get('pacientes', request['paciente_id'])
            msg = self.output(p, 'espera', f"Horário disponível em {timestamp(a['inicio']).strftime('%d/%m %H:%M')}. Responda 1 para agendar.", inicio=a['inicio'], profissional=a['profissional'], servico=a['servico'], modalidade=a['modalidade'])
            if msg:
                request['status'] = 'ofertado'
                d.save('espera', request)
                break
        return a

    def presence(self, a):
        d = self.d
        service = d.get('servicos', a['servico'])
        if a['status'] == 'realizado' and service.get('retorno_dias') is not None:
            if not any(r['agendamento_id'] == a['id'] for r in d.all('retornos')):
                d.save('retornos', dict(paciente_id=a['paciente_id'], agendamento_id=a['id'], servico=a['servico'],
                    data_origem=a['inicio'][:10], data=(timestamp(a['inicio']) + timedelta(days=service['retorno_dias'])).strftime('%Y-%m-%d'), avisado=False))

    def run(self, body):
        d = self.d
        instant = timestamp(body['agora']) if 'agora' in body else now()
        retried = 0
        # Apenas pendências anteriores à rodada: uma nova falha espera a próxima execução.
        for message in d.all('saida'):
            if message['status'] != 'pendente' or not message['telefone']:
                continue
            patient = next((p for p in d.all('pacientes') if p['telefone'] == message['telefone']), None)
            if patient and patient['nao_contatar'] and message['tipo'] != 'humano':
                continue
            status = send_whatsapp(message['telefone'], message['texto'])
            if status == 'enviado':
                message['status'] = status
                d.save('saida', message)
                retried += 1
        count = 0
        for a in d.all('agendamentos'):
            if a['status'] != 'agendado' or a.get('confirmacao_enviada') or not instant < timestamp(a['inicio']) <= instant + timedelta(hours=d.config['confirmacao_horas']):
                continue
            p = d.get('pacientes', a['paciente_id'])
            service = d.get('servicos', a['servico'])
            text = f"{service['nome']} em {timestamp(a['inicio']).strftime('%d/%m %H:%M')}. Responda 1 para confirmar ou 2 para cancelar."
            if a['modalidade'] == 'online':
                text += ' Consulta online: ' + (a['link'] or 'a equipe enviará o link.')
            msg = self.output(p, 'confirmacao', text, instant, inicio=a['inicio'])
            if msg:
                msg['agendamento_id'] = a['id']
                d.save('saida', msg)
                a['confirmacao_enviada'] = True
                d.save('agendamentos', a)
                count += 1
        for r in d.all('retornos'):
            if r['avisado'] or instant.date() < (timestamp(r['data'] + 'T00:00') - timedelta(days=d.config['retorno_aviso_dias'])).date():
                continue
            p = d.get('pacientes', r['paciente_id'])
            if self.output(p, 'retorno', f"É hora de agendar seu retorno de {d.get('servicos', r['servico'])['nome']}.", instant):
                r['avisado'] = True
                d.save('retornos', r)
                count += 1
        from .nutrition import Nutrition, meal_line
        nutrition = Nutrition(d)
        for p in d.all('pacientes'):
            goals = nutrition.goals(p['id'])
            reminders = [('agua:' + h, h, 'Lembrete de água.') for h in goals['lembretes_agua']]
            plan = nutrition.active(p['id'])
            if goals['lembretes_refeicoes'] and plan:
                reminders.extend(('refeicao:' + m['nome'], m['horario'], meal_line(m)) for m in plan['refeicoes'])
            for key, h, text in reminders:
                target = timestamp(instant.strftime('%Y-%m-%d') + 'T' + h)
                marker = f"{p['id']}:{instant.strftime('%Y-%m-%d')}:{key}"
                if not target <= instant <= target + timedelta(minutes=d.config['lembrete_tolerancia_min']):
                    continue
                if any(r['id'] == marker for r in d.all('lembretes_enviados')):
                    continue
                if self.output(p, 'lembrete', text, instant):
                    d.save('lembretes_enviados', {'id': marker})
                    count += 1
        return {'enviadas': count, 'reenviadas': retried}

    def route(self, method, path, body):
        d = self.d
        if path == '/api/saida' and method == 'GET':
            return 200, {'mensagens': d.all('saida')}
        if path == '/api/tarefas/rodar' and method == 'POST':
            return 200, self.run(body)
        if path == '/api/espera' and method == 'POST':
            required(body, 'paciente_id', 'servico', 'data')
            d.get('pacientes', body['paciente_id'])
            d.get('servicos', body['servico'])
            timestamp(body['data'] + 'T00:00')
            return 201, d.save('espera', dict(paciente_id=body['paciente_id'], servico=body['servico'], data=body['data'], status='aguardando'))
        return None
