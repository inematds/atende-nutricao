"""Edição dos cadastros e bloqueios, preservando referências históricas."""
import re
from datetime import datetime
from .domain import phone, required, timestamp
from .storage import Error


def text(value):
    return isinstance(value, str) and bool(value.strip())


def positive(value):
    return type(value) is int and value > 0


def schedule(value):
    if value is None:
        return
    if not isinstance(value, dict):
        raise Error(422, 'Horários inválidos')
    for day, windows in value.items():
        if day not in ('seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom') or not isinstance(windows, list):
            raise Error(422, 'Horários inválidos')
        for window in windows:
            if not isinstance(window, list) or len(window) != 2:
                raise Error(422, 'Janela inválida')
            for hour in window:
                if not isinstance(hour, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', hour):
                    raise Error(422, 'Horário inválido')
            if window[0] >= window[1]:
                raise Error(422, 'Janela inválida')


class Registrations:
    def __init__(self, domain):
        self.d = domain

    def route(self, method, path, query, body):
        d = self.d
        match = re.fullmatch(r'/api/(profissionais|servicos|faq|pacientes|bloqueios)(?:/([^/]+))?', path)
        if not match:
            return None
        collection, key = match.groups()
        if collection == 'pacientes':
            if method != 'PUT' or key is None:
                return None
            row = d.get(collection, key)
            changes = {k: v for k, v in body.items() if k in ('nome', 'telefone', 'email', 'nascimento', 'consentimento_marketing', 'nao_contatar')}
            if 'telefone' in changes:
                changes['telefone'] = phone(changes['telefone'])
                if any(p['id'] != row['id'] and p['telefone'] == changes['telefone'] for p in d.all(collection)):
                    raise Error(409, 'Telefone já cadastrado')
            if 'nome' in changes and not text(changes['nome']):
                raise Error(422, 'Nome inválido')
            for field in ('consentimento_marketing', 'nao_contatar'):
                if field in changes and type(changes[field]) is not bool:
                    raise Error(422, 'Preferência inválida')
            if changes.get('nascimento') is not None:
                birth = changes['nascimento']
                if not isinstance(birth, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', birth):
                    raise Error(422, 'Nascimento inválido')
                datetime.strptime(birth, '%Y-%m-%d')
            return 200, d.save(collection, dict(row, **changes))
        if collection == 'bloqueios':
            if method == 'GET' and key is None:
                if query.get('profissional'):
                    d.get('profissionais', query['profissional'])
                rows = [b for b in d.all(collection) if not query.get('profissional') or b['profissional'] == query['profissional']]
                return 200, {'bloqueios': sorted(rows, key=lambda b: (b['inicio'], b['id']))}
            if method == 'POST' and key is None:
                required(body, 'profissional', 'inicio', 'fim', 'motivo')
                d.get('profissionais', body['profissional'])
                if timestamp(body['inicio']) >= timestamp(body['fim']):
                    raise Error(422, 'Intervalo inválido')
                row = d.save(collection, {k: body[k] for k in ('profissional', 'inicio', 'fim', 'motivo')})
                conflicts = [a['id'] for a in d.all('agendamentos') if a['status'] != 'cancelado' and a['profissional'] == row['profissional'] and a['inicio'] < row['fim'] and a['fim'] > row['inicio']]
                return 201, {'id': row['id'], 'conflitos': conflicts}
            if method == 'DELETE' and key is not None:
                d.get(collection, key)
                d.delete(collection, key)
                return 204, None
            return None
        if method == 'DELETE' and key is not None:
            row = d.get(collection, key)
            if collection == 'faq':
                d.delete(collection, key)
                return 204, None
            d.save(collection, dict(row, ativo=False))
            return 200, {'ativo': False}
        creating = method == 'POST' and key is None
        updating = method == 'PUT' and key is not None and collection != 'faq'
        if not creating and not updating:
            return None
        fields = {'profissionais': ('nome', 'servicos', 'registro', 'horarios'),
                  'servicos': ('nome', 'duracao_min', 'retorno_dias'),
                  'faq': ('perguntas', 'resposta')}[collection]
        if creating:
            required(body, *({'profissionais': ('id', 'nome', 'servicos'), 'servicos': ('id', 'nome', 'duracao_min'), 'faq': ('perguntas', 'resposta')}[collection]))
            row = {}
            if collection != 'faq':
                if not text(body['id']):
                    raise Error(422, 'Id inválido')
                if any(x['id'] == body['id'] for x in d.all(collection)):
                    raise Error(409, 'Id já cadastrado')
                row = {'id': body['id'], 'ativo': True}
            if collection == 'profissionais':
                row.update(registro=None, horarios=None)
            if collection == 'servicos':
                row['retorno_dias'] = None
        else:
            row = d.get(collection, key)
        row.update({k: body[k] for k in fields if k in body})
        if collection != 'faq' and not text(row['nome']):
            raise Error(422, 'Nome inválido')
        if collection == 'profissionais':
            services = row['servicos']
            if not isinstance(services, list) or any(s not in [x['id'] for x in d.all('servicos')] for s in services):
                raise Error(422, 'Serviço inválido')
            schedule(row['horarios'])
        elif collection == 'servicos':
            if not positive(row['duracao_min']) or (row['retorno_dias'] is not None and not positive(row['retorno_dias'])):
                raise Error(422, 'Duração ou retorno inválido')
        elif not isinstance(row['perguntas'], list) or not row['perguntas'] or not all(text(q) for q in row['perguntas']) or not text(row['resposta']):
            raise Error(422, 'FAQ inválido')
        return (201 if creating else 200), d.save(collection, row)
