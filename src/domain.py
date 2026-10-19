"""Cadastros básicos e regras da agenda do consultório."""
import os
import re
import unicodedata
from datetime import datetime, timedelta
from .storage import Error


def now():
    return datetime.fromisoformat(os.environ['ATENDE_AGORA']) if os.environ.get('ATENDE_AGORA') else datetime.now().replace(second=0, microsecond=0)


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', value):
        raise Error(422, 'Data/hora inválida')
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise Error(422, 'Data/hora inválida')


def phone(value):
    if not isinstance(value, str):
        raise Error(400, 'Telefone inválido')
    digits = re.sub(r'\D', '', value)
    if len(digits) in (10, 11):
        return '+55' + digits
    if len(digits) in (12, 13) and digits.startswith('55'):
        return '+' + digits
    raise Error(400, 'Telefone inválido')


def required(body, *keys):
    if any(k not in body for k in keys):
        raise Error(422, 'Campos obrigatórios ausentes')


class Domain:
    def __init__(self, store, db):
        self.store, self.db, self.config = store, db, store.config

    def all(self, collection):
        return self.store.all(self.db, collection)

    def get(self, collection, key):
        return self.store.get(self.db, collection, key)

    def save(self, collection, entry):
        return self.store.save(self.db, collection, entry)

    def patient(self, body):
        required(body, 'nome', 'telefone')
        number = phone(body['telefone'])
        for p in self.all('pacientes'):
            if p['telefone'] == number:
                return 200, {'id': p['id']}
        p = self.save('pacientes', dict(nome=body['nome'], telefone=number,
                      email=body.get('email'), nascimento=body.get('nascimento'),
                      consentimento_marketing=bool(body.get('consentimento_marketing', False)),
                      nao_contatar=any(x['id'] == number and x['nao_contatar'] for x in self.all('preferencias'))))
        return 201, {'id': p['id']}

    def candidates(self, service, professional, day):
        date = datetime.strptime(day, '%Y-%m-%d')
        if not service['ativo'] or not professional['ativo'] or service['id'] not in professional['servicos'] or day in self.config['feriados']:
            return []
        schedule = professional.get('horarios') or self.config['horarios']
        weekday = ('seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom')[date.weekday()]
        duration = timedelta(minutes=service['duracao_min'])
        earliest = now() + timedelta(hours=self.config['antecedencia_min_horas'])
        result = []
        for start, end in schedule.get(weekday, []):
            cursor, limit = timestamp(day + 'T' + start), timestamp(day + 'T' + end)
            while cursor + duration <= limit:
                finish = cursor + duration
                blocked = any(b['profissional'] == professional['id'] and cursor < timestamp(b['fim']) and finish > timestamp(b['inicio']) for b in self.all('bloqueios'))
                if cursor >= earliest and not blocked:
                    result.append(cursor.isoformat(timespec='minutes'))
                cursor += timedelta(minutes=self.config['passo_min'])
        return result

    def occupied(self, professional, start, end, ignore=None):
        return any(a['id'] != ignore and a['profissional'] == professional and a['status'] != 'cancelado'
                   and start < a['fim'] and end > a['inicio'] for a in self.all('agendamentos'))

    def slots(self, query):
        required(query, 'servico', 'data')
        service = self.get('servicos', query['servico'])
        professionals = [self.get('profissionais', query['profissional'])] if query.get('profissional') else self.all('profissionais')
        slots = []
        for p in professionals:
            for start in self.candidates(service, p, query['data']):
                end = (timestamp(start) + timedelta(minutes=service['duracao_min'])).isoformat(timespec='minutes')
                if not self.occupied(p['id'], start, end):
                    slots.append({'inicio': start, 'profissional': p['id']})
        return sorted(slots, key=lambda h: h['inicio'])

    def book(self, body, previous=None):
        required(body, 'paciente_id', 'servico', 'inicio')
        self.get('pacientes', body['paciente_id'])
        service = self.get('servicos', body['servico'])
        professionals = [self.get('profissionais', body['profissional'])] if body.get('profissional') else self.all('profissionais')
        start = timestamp(body['inicio'])
        mode = body.get('modalidade', 'presencial')
        if mode not in ('presencial', 'online') or (mode == 'online' and not self.config['atende_online']):
            raise Error(422, 'Modalidade inválida')
        end = (start + timedelta(minutes=service['duracao_min'])).isoformat(timespec='minutes')
        valid = False
        for p in professionals:
            if body['inicio'] not in self.candidates(service, p, body['inicio'][:10]):
                continue
            valid = True
            if self.occupied(p['id'], body['inicio'], end, previous['id'] if previous else None):
                continue
            appointment = dict(paciente_id=body['paciente_id'], servico=service['id'], inicio=body['inicio'],
                               fim=end, profissional=p['id'], modalidade=mode, link=previous['link'] if previous else None, status='agendado')
            if previous:
                appointment['id'] = previous['id']
            return self.save('agendamentos', appointment)
        raise Error(409 if valid else 422, 'Horário ocupado' if valid else 'Horário inválido')

    def appointments(self, query):
        result = []
        for a in self.all('agendamentos'):
            day = a['inicio'][:10]
            if query.get('data') and day != query['data']:
                continue
            if query.get('de', day) > day or query.get('ate', day) < day:
                continue
            if query.get('profissional', a['profissional']) != a['profissional']:
                continue
            p = self.get('pacientes', a['paciente_id'])
            result.append(dict(a, nome=p['nome'], telefone=p['telefone']))
        return sorted(result, key=lambda a: (a['inicio'], a['id']))

    def cancel(self, appointment):
        from .tasks import Tasks
        return Tasks(self).cancel(appointment)

    def route(self, method, path, query, body):
        from .conversation import Conversation
        from .tasks import Tasks
        from .nutrition import Nutrition
        nutrition_result = Nutrition(self).route(method, path, query, body)
        if nutrition_result is not None:
            return nutrition_result
        task_result = Tasks(self).route(method, path, body)
        if task_result is not None:
            return task_result
        if path == '/api/mensagens' and method == 'POST':
            return 200, Conversation(self).message(body)
        if path == '/api/atendimento-humano' and method == 'GET':
            return 200, {'fila': [r for r in self.all('atendimentos') if r['status'] == 'aberto']}
        human_match = re.fullmatch(r'/api/atendimento-humano/([^/]+)/(responder|encerrar)', path)
        if human_match and method == 'POST':
            row = self.get('atendimentos', human_match[1])
            if human_match[2] == 'encerrar':
                row['status'] = 'encerrado'
                self.save('atendimentos', row)
            else:
                required(body, 'texto')
                if not isinstance(body['texto'], str) or not body['texto'].strip():
                    raise Error(422, 'Texto vazio')
                p = next((p for p in self.all('pacientes') if p['telefone'] == row['telefone']), None)
                Tasks(self).output(p or {'id': None, 'telefone': row['telefone'], 'nao_contatar': False}, 'humano', body['texto'])
            return 200, row
        if path == '/api/servicos' and method == 'GET':
            return 200, {'servicos': [s for s in self.all('servicos') if s['ativo']]}
        if path == '/api/profissionais' and method == 'GET':
            return 200, {'profissionais': self.all('profissionais')}
        if path == '/api/faq' and method == 'GET':
            return 200, {'faq': self.all('faq')}
        if path == '/api/horarios' and method == 'GET':
            return 200, {'horarios': self.slots(query)}
        if path == '/api/pacientes':
            if method == 'POST':
                return self.patient(body)
            if method == 'GET':
                term = normalized(query.get('busca', ''))
                digits = re.sub(r'\D', '', term)
                return 200, {'pacientes': [p for p in self.all('pacientes') if term in normalized(p['nome']) or (digits and digits in (p['telefone'] or ''))]}
        if path == '/api/agendamentos':
            if method == 'POST':
                return 201, self.book(body)
            if method == 'GET':
                return 200, {'agendamentos': self.appointments(query)}
        match = re.fullmatch(r'/api/agendamentos/([^/]+)/(cancelar|remarcar|presenca|link)', path)
        if match and method == 'POST':
            a = self.get('agendamentos', match[1])
            action = match[2]
            if action == 'cancelar':
                return 200, self.cancel(a)
            elif action == 'remarcar':
                required(body, 'inicio')
                return 200, self.book(dict(a, inicio=body['inicio']), previous=a)
            elif action == 'presenca':
                required(body, 'compareceu')
                if not isinstance(body['compareceu'], bool):
                    raise Error(422, 'Compareceu deve ser booleano')
                a['status'] = 'realizado' if body['compareceu'] else 'falta'
                Tasks(self).presence(a)
            elif action == 'link':
                if a['modalidade'] != 'online' or not isinstance(body.get('link'), str) or not body['link'].strip():
                    raise Error(422, 'Link inválido')
                a['link'] = body['link']
            return 200, self.save('agendamentos', a)
        raise Error(404, 'Rota não implementada')
