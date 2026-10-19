"""Campanhas, anonimização e indicadores agregados do consultório."""
import calendar
import json
import re
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from .domain import normalized, timestamp, required
from .nutrition import rounded
from .storage import Error
from .tasks import Tasks


def percentage(numerator, denominator):
    return rounded(Decimal(numerator) * 100 / Decimal(denominator)) if denominator else 0


class Reporting:
    def __init__(self, domain):
        self.d = domain

    def campaign(self, body):
        text = body.get('texto')
        if not isinstance(text, str) or not text.strip():
            raise Error(422, 'Texto obrigatório')
        clean = normalized(text)
        rules = {'promessa_resultado': ('garantido', 'garantia de resultado', 'resultado garantido', 'garantimos', '100%'),
                 'antes_depois': ('antes e depois',)}
        violations = [code for code, terms in rules.items() if any(term in clean for term in terms)]
        if violations:
            return 422, {'violacoes': violations}
        count = 0
        for patient in self.d.all('pacientes'):
            if patient['consentimento_marketing'] and Tasks(self.d).output(patient, 'campanha', text):
                count += 1
        return 200, {'enviadas': count}

    def erase(self, patient):
        d = self.d
        pid, number = patient['id'], patient['telefone']
        patient.update(nome='removido', telefone=None, email=None, nascimento=None,
                       consentimento_marketing=False, nao_contatar=True)
        d.save('pacientes', patient)
        for appointment in d.all('agendamentos'):
            if appointment['paciente_id'] == pid:
                if appointment['status'] in ('agendado', 'confirmado'):
                    appointment['status'] = 'cancelado'
                appointment['link'] = None
                d.save('agendamentos', appointment)
        for collection in ('mensagens', 'saida'):
            for row in d.all(collection):
                if row.get('paciente_id') == pid or (number is not None and row.get('telefone') == number):
                    row.update(paciente_id=pid, telefone=None, texto='')
                    d.save(collection, row)
        for collection in ('planos', 'diario', 'espera'):
            for row in d.all(collection):
                if row['paciente_id'] == pid:
                    d.delete(collection, row['id'])
        d.delete('metas', pid)
        if number is not None:
            d.delete('conversas', number)
            d.delete('preferencias', number)
            for row in d.all('atendimentos'):
                if row['telefone'] == number:
                    d.delete('atendimentos', row['id'])
        for row in d.all('lembretes_enviados'):
            if str(row['id']).startswith(str(pid) + ':'):
                d.delete('lembretes_enviados', row['id'])

    def report(self, month):
        if not isinstance(month, str) or not re.fullmatch(r'\d{4}-\d{2}', month):
            raise Error(422, 'Mês inválido')
        year, num = map(int, month.split('-'))
        start = date(year, num, 1)
        days = calendar.monthrange(year, num)[1]
        all_appointments = self.d.all('agendamentos')
        monthly = [a for a in all_appointments if a['inicio'][:7] == month]
        performed = [a for a in all_appointments if a['status'] == 'realizado']
        done = sum(a['status'] == 'realizado' for a in monthly)
        missed = sum(a['status'] == 'falta' for a in monthly)
        minutes = sum(int((timestamp(a['fim']) - timestamp(a['inicio'])).total_seconds() / 60)
                      for a in monthly if a['status'] != 'cancelado')
        available = 0
        for professional in self.d.all('profissionais'):
            if not professional['ativo']:
                continue
            schedule = professional.get('horarios')
            if schedule is None:
                schedule = self.d.config['horarios']
            for offset in range(days):
                day = start + timedelta(days=offset)
                if day.isoformat() in self.d.config['feriados']:
                    continue
                weekday = ('seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom')[day.weekday()]
                for begin, end in schedule.get(weekday, []):
                    available += int((timestamp(f'{day}T{end}') - timestamp(f'{day}T{begin}')).total_seconds() / 60)
        first = {}
        for a in performed:
            pid = a['paciente_id']
            first[pid] = min(first.get(pid, a['inicio']), a['inicio'])
        returns = [r for r in self.d.all('retornos') if r['data'][:7] == month]
        fulfilled = sum(any(a['paciente_id'] == r['paciente_id'] and a['id'] != r['agendamento_id']
                            and date.fromisoformat(r['data_origem']) < date.fromisoformat(a['inicio'][:10])
                            <= date.fromisoformat(r['data']) + timedelta(days=30)
                            for a in performed) for r in returns)
        return {'pacote': 'clinica', 'mes': month, 'valores': {
            'atendimentos_mes': done, 'falta_pct': percentage(missed, done + missed),
            'ocupacao_pct': percentage(minutes, available),
            'clientes_novos_mes': sum(value[:7] == month for value in first.values()),
            'retorno_atual_pct': percentage(fulfilled, len(returns))}}

    def export(self, month, filename):
        values = self.report(month)['valores']
        path = Path(filename)
        document = json.loads(path.read_text(encoding='utf-8'))
        months = document.get('meses', [])
        previous = sorted((m for m in months if m['mes'] < month), key=lambda m: m['mes'])
        inherited = previous[-1]['valores'] if previous else document['base']['valores']
        entry = {'mes': month, 'valores': dict(inherited, **values), 'obs': 'atende-nutricao'}
        document['meses'] = sorted([m for m in months if m['mes'] != month] + [entry], key=lambda m: m['mes'])
        temporary = path.with_name(path.name + '.tmp')
        temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)

    def route(self, method, path, query, body):
        if path == '/api/campanhas' and method == 'POST':
            return self.campaign(body)
        if path == '/api/raiox' and method == 'GET':
            required(query, 'mes')
            return 200, self.report(query['mes'])
        match = re.fullmatch(r'/api/pacientes/([^/]+)', path)
        if match and method == 'DELETE':
            self.erase(self.d.get('pacientes', match[1]))
            return 204, None
        return None
