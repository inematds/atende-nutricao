"""Planos autorais, metas e diário: armazenamento sem prescrição."""
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from .domain import now, timestamp, required
from .storage import Error


def rounded(value):
    return float(Decimal(str(value)).quantize(Decimal('.1'), rounding=ROUND_HALF_UP))


def hour(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
        raise Error(422, 'Horário inválido')
    return value


def meal_line(meal):
    return f"{meal['horario']} {meal['nome']}: {' / '.join(meal['opcoes'])}" + (' — ' + meal['observacoes'] if meal['observacoes'] else '')


def plan_text(plan):
    lines = [f"Seu plano alimentar (versão {plan['versao']}, de {timestamp(plan['criado_em']).strftime('%d/%m/%Y')}):"]
    lines.extend(meal_line(m) for m in plan['refeicoes'])
    if plan['observacoes']:
        lines.append(plan['observacoes'])
    return '\n'.join(lines)


class Nutrition:
    def __init__(self, domain):
        self.d = domain

    def plans(self, pid):
        return sorted((p for p in self.d.all('planos') if p['paciente_id'] == pid), key=lambda p: p['versao'])

    def active(self, pid):
        plans = self.plans(pid)
        return plans[-1] if plans else None

    def goals(self, pid):
        row = next((r for r in self.d.all('metas') if r['id'] == pid), {})
        return {k: row.get(k, default) for k, default in dict(lembretes_agua=[], lembretes_refeicoes=False, meta_agua_copos=None).items()}

    def entries(self, pid, query=None):
        query = query or {}
        return sorted((r for r in self.d.all('diario') if r['paciente_id'] == pid and query.get('de', '') <= r['quando'][:10] <= query.get('ate', '9999-12-31')), key=lambda r: (r['quando'], r['id']))

    def diary(self, pid, query):
        rows = self.entries(pid, query)
        done = sum(r['tipo'] == 'refeicao' and r['status'] == 'feita' for r in rows)
        skipped = sum(r['tipo'] == 'refeicao' and r['status'] == 'pulada' for r in rows)
        return {'registros': rows, 'resumo': dict(agua_copos=sum(r['valor'] for r in rows if r['tipo'] == 'agua'), refeicoes_feitas=done, refeicoes_puladas=skipped, adesao_pct=rounded(100 * done / (done + skipped)) if done + skipped else 0, fotos=sum(r['tipo'] == 'foto' for r in rows))}

    def weights(self, pid):
        rows = [dict(id=r['id'], quando=r['quando'], peso=r['valor'], origem=r['origem']) for r in self.entries(pid) if r['tipo'] == 'peso']
        return {'pesos': rows, 'variacao': rounded(Decimal(str(rows[-1]['peso'])) - Decimal(str(rows[0]['peso']))) if len(rows) >= 2 else None}

    def record(self, pid, kind, **fields):
        row = dict(paciente_id=pid, tipo=kind, quando=now().isoformat(timespec='minutes'), valor=None, refeicao=None, status=None, mimetype=None, caption=None, message_id=None, origem='chat')
        row.update(fields)
        return self.d.save('diario', row)

    def weight(self, pid, value, origin, when=None):
        try:
            if isinstance(value, bool):
                raise ValueError()
            numeric = Decimal(str(value))
            if not numeric.is_finite() or not Decimal(20) <= numeric <= Decimal(400):
                raise ValueError()
        except (InvalidOperation, ValueError):
            raise Error(422, 'Peso deve estar entre 20 e 400')
        when = timestamp(when).isoformat(timespec='minutes') if when is not None else now().isoformat(timespec='minutes')
        return self.record(pid, 'peso', valor=rounded(numeric), origem=origin, quando=when)

    def match_meal(self, plan, text):
        from .conversation import significant
        words = set(text.split())
        scores = [(len(significant(m['nome']) & words), m) for m in plan['refeicoes']]
        best = max(scores, key=lambda pair: pair[0])
        return best[1] if best[0] else None

    def chat_record(self, p, text):
        if not p:
            return 'É necessário seu cadastro para registrar o diário.'
        pid, words = p['id'], set(text.split())
        number = re.search(r'\d+(?:[.,]\d+)?', text)
        if words & {'kg', 'quilo', 'quilos', 'peso', 'pesei', 'pesando'} and number:
            try:
                r = self.weight(pid, number[0].replace(',', '.'), 'chat')
            except Error:
                return 'Informe um peso entre 20 e 400 kg.'
            return f"Peso registrado: {r['valor']:.1f} kg.".replace('.', ',', 1)
        if 'peso' in words and not number:
            weights = self.weights(pid)['pesos']
            return (f"{weights[-1]['peso']:.1f} kg".replace('.', ',') if weights else 'Nenhum peso registrado.')
        if words & {'copo', 'copos'}:
            integer = re.search(r'\d+', text)
            self.record(pid, 'agua', valor=int(integer[0]) if integer else 1)
            day = now().strftime('%Y-%m-%d')
            total = self.diary(pid, {'de': day, 'ate': day})['resumo']['agua_copos']
            goal = self.goals(pid)['meta_agua_copos']
            return f"Água registrada: {total} de {goal} copos." if goal else f"Água registrada: {total} copos."
        plan = self.active(pid)
        if not plan:
            return 'Peça ao nutricionista para registrar seu plano alimentar.'
        meal = self.match_meal(plan, text)
        if not meal:
            eligible = [m for m in plan['refeicoes'] if m['horario'] <= now().strftime('%H:%M')]
            meal = eligible[-1] if eligible else plan['refeicoes'][0]
        status = 'pulada' if any(t in text for t in ('pulei', 'pulou', 'nao comi', 'nao fiz', 'nao tomei')) else 'feita'
        self.record(pid, 'refeicao', refeicao=meal['nome'], status=status)
        return f"Refeição registrada: {meal['nome']} ({status})."

    def chat_plan(self, p, text, conversation, number):
        plan = self.active(p['id']) if p else None
        if not plan:
            return 'Peça ao nutricionista para registrar seu plano alimentar.'
        meal = self.match_meal(plan, text)
        if meal:
            return meal_line(meal)
        if any(t in text for t in ('posso comer', 'pode comer', 'o que comer', 'o que como')):
            conversation.human(number, 'duvida_plano')
            return 'Essa dúvida está fora do plano. Vou chamar um atendente e o nutricionista.'
        return plan_text(plan)

    def route(self, method, path, query, body):
        match = re.fullmatch(r'/api/pacientes/([^/]+)/(plano(?:/enviar)?|planos|diario|pesos|metas|dados)', path)
        if not match:
            return None
        p = self.d.get('pacientes', match[1])
        pid, action = p['id'], match[2]
        if action == 'dados' and method == 'GET':
            return 200, dict(paciente=p, agendamentos=[a for a in self.d.appointments({}) if a['paciente_id'] == pid], mensagens=[m for m in self.d.all('mensagens') if m['telefone'] == p['telefone']], planos=self.plans(pid), diario=self.entries(pid), pesos=self.weights(pid)['pesos'], metas=self.goals(pid))
        if action == 'plano' and method == 'POST':
            meals = body.get('refeicoes')
            if not isinstance(meals, list) or not meals:
                raise Error(422, 'Refeições obrigatórias')
            validated = []
            for meal in meals:
                if not isinstance(meal, dict):
                    raise Error(422, 'Refeição inválida')
                hour(meal.get('horario'))
                if not isinstance(meal.get('nome'), str) or not meal['nome'].strip() or not isinstance(meal.get('opcoes'), list) or not meal['opcoes'] or any(not isinstance(o, str) or not o.strip() for o in meal['opcoes']):
                    raise Error(422, 'Nome e opções obrigatórios')
                if not isinstance(meal.get('observacoes', ''), str):
                    raise Error(422, 'Observações inválidas')
                validated.append(dict(horario=meal['horario'], nome=meal['nome'], opcoes=meal['opcoes'], observacoes=meal.get('observacoes', '')))
            if not isinstance(body.get('observacoes', ''), str):
                raise Error(422, 'Observações inválidas')
            return 201, self.d.save('planos', dict(paciente_id=pid, versao=len(self.plans(pid))+1, refeicoes=sorted(validated, key=lambda m: m['horario']), observacoes=body.get('observacoes', ''), criado_em=now().isoformat(timespec='minutes'), enviado_em=None))
        if action in ('plano', 'plano/enviar'):
            plan = self.active(pid)
            if not plan:
                raise Error(404, 'Plano inexistente')
            if action == 'plano' and method == 'GET':
                return 200, plan
            if action == 'plano/enviar' and method == 'POST':
                if p['nao_contatar']:
                    raise Error(409, 'nao_contatar')
                from .tasks import Tasks
                Tasks(self.d).output(p, 'plano', plan_text(plan))
                plan['enviado_em'] = now().isoformat(timespec='minutes')
                self.d.save('planos', plan)
                return 200, {'enviadas': 1}
        if action == 'planos' and method == 'GET':
            return 200, {'planos': self.plans(pid)}
        if action == 'diario' and method == 'GET':
            return 200, self.diary(pid, query)
        if action == 'pesos':
            if method == 'GET':
                return 200, self.weights(pid)
            if method == 'POST':
                required(body, 'peso')
                return 201, self.weight(pid, body['peso'], 'equipe', body.get('quando'))
        if action == 'metas' and method in ('GET', 'PUT'):
            goals = self.goals(pid)
            if method == 'PUT':
                goals.update({k: body[k] for k in goals if k in body})
                if not isinstance(goals['lembretes_agua'], list) or not isinstance(goals['lembretes_refeicoes'], bool):
                    raise Error(422, 'Lembretes inválidos')
                for h in goals['lembretes_agua']:
                    hour(h)
                target = goals['meta_agua_copos']
                if target is not None and (type(target) is not int or target <= 0):
                    raise Error(422, 'Meta inválida')
                self.d.save('metas', dict(goals, id=pid))
            return 200, goals
        raise Error(404, 'Rota inexistente')
