"""Conversa determinística, com fluxo e histórico persistentes."""
import re
from datetime import timedelta
from .domain import normalized, now, phone, required, timestamp
from .storage import Error

EMERGENCIAS = ('dor no peito', 'falta de ar', 'desmaio', 'desmaiei', 'desmaiou', 'convulsao', 'sangramento', 'sangrando', 'infarto', 'avc', 'nao paro de vomitar', 'vomitando sem parar', 'vomito sem parar', 'hipoglicemia', 'suor frio', 'visao turva', 'tremedeira')
ALERTAS = ('me matar', 'suicidio', 'me machucar', 'me cortar', 'compulsao', 'vomitei de proposito', 'forcei o vomito', 'provoquei o vomito', 'laxante', 'parei de comer', 'nao como ha dias', 'sem comer ha dias', 'jejum de dias')
IGNORADAS = set('que quem qual quais onde como quando uma umas uns voce voces vcs seu sua seus suas meu minha meus minhas nos nosso nossa esse essa isso este esta tem fica para com por dos das de do da pre pos'.split())


def normalize(text):
    text = normalized(text)
    return ' '.join(''.join(c if c.isalnum() or c.isspace() or (c in ',.' and i > 0 and i + 1 < len(text) and text[i-1].isdigit() and text[i+1].isdigit()) else ' ' for i, c in enumerate(text)).split())


def significant(text):
    return {w for w in normalize(text).split() if len(w) >= 3 and w not in IGNORADAS}


class Conversation:
    def __init__(self, domain):
        self.d = domain

    def human(self, number, reason, priority='normal'):
        d = self.d
        row = next((r for r in d.all('atendimentos') if r['telefone'] == number and r['status'] == 'aberto'), None)
        if row:
            if priority == 'alta':
                row.update(prioridade=priority, motivo=reason)
                d.save('atendimentos', row)
            return row
        p = next((p for p in d.all('pacientes') if p['telefone'] == number), None)
        row = d.save('atendimentos', dict(telefone=number, nome=p['nome'] if p else None, motivo=reason, prioridade=priority, status='aberto'))
        from .telegram import Telegram
        entries = [m for m in d.all('mensagens') if m['telefone'] == number and m['direcao'] == 'entrada']
        Telegram(d).forward(row, entries[-1]['texto'] if entries else '', opening=True)
        return row

    def message(self, body):
        required(body, 'telefone', 'texto')
        if not isinstance(body['texto'], str):
            raise Error(422, 'Texto inválido')
        d = self.d
        number, original = phone(body['telefone']), body['texto']
        text = normalize(original)
        state = next((s for s in d.all('conversas') if s['id'] == number), {'id': number, 'fluxo': None, 'nao_entendi': 0})
        patient = next((p for p in d.all('pacientes') if p['telefone'] == number), None)
        d.save('mensagens', dict(telefone=number, direcao='entrada', texto=original, quando=now().isoformat(timespec='minutes')))
        opened = next((r for r in d.all('atendimentos') if r['telefone'] == number and r['status'] == 'aberto'), None)
        previous_misses = state['nao_entendi']
        state['nao_entendi'] = 0
        answer = self.decide(number, original, text, state, patient, previous_misses)
        if opened:
            from .telegram import Telegram
            Telegram(d).forward(d.get('atendimentos', opened['id']), original)
        d.save('conversas', state)
        responses = [] if answer is None else [answer]
        for response in responses:
            d.save('mensagens', dict(telefone=number, direcao='saida', texto=response, quando=now().isoformat(timespec='minutes')))
        return {'respostas': responses}

    def decide(self, number, original, text, state, p, misses):
        d = self.d
        if any(t in text for t in EMERGENCIAS):
            self.human(number, 'emergencia', 'alta')
            return 'Ligue 192 ou procure um pronto-socorro. A equipe foi avisada.'
        if any(t in text for t in ALERTAS):
            self.human(number, 'alerta', 'alta')
            return 'Você pode ligar 188 (CVV). Vou chamar o nutricionista e a equipe.'
        if any(r['telefone'] == number and r['status'] == 'aberto' for r in d.all('atendimentos')):
            return None
        if text in ('parar', 'sair', 'pare'):
            d.save('preferencias', {'id': number, 'nao_contatar': True})
            if p:
                p['nao_contatar'] = True
                d.save('pacientes', p)
            return 'Você não vai mais receber mensagens automáticas.'
        if text == 'parar lembretes':
            if p:
                metas = next((m for m in d.all('metas') if m['id'] == p['id']), {'id': p['id'], 'meta_agua_copos': None})
                metas.update(lembretes_agua=[], lembretes_refeicoes=False)
                d.save('metas', metas)
            return 'Seus lembretes foram desativados.'
        if any(t in text for t in ('atendente', 'humano', 'falar com alguem')):
            self.human(number, 'atendente')
            return 'Vou chamar um atendente.'
        if state['fluxo']:
            return self.flow(number, original, text, state, p)
        pending = [m for m in d.all('saida') if m['telefone'] == number]
        if pending and not pending[-1].get('respondida'):
            m = pending[-1]
            if m['tipo'] == 'confirmacao' and text in ('1', 'sim', 'confirmo', '2', 'cancelar', 'nao'):
                a = d.get('agendamentos', m['agendamento_id'])
                if a['status'] == 'agendado' and a['inicio'] == m['inicio']:
                    m['respondida'] = True
                    d.save('saida', m)
                    if text in ('1', 'sim', 'confirmo'):
                        a['status'] = 'confirmado'
                        d.save('agendamentos', a)
                        return 'Agendamento confirmado.'
                    d.cancel(a)
                    from .telegram import Telegram
                    Telegram(d).appointment(a, cancelled=True)
                    return 'Agendamento cancelado.'
            if m['tipo'] == 'espera' and text in ('1', 'sim'):
                m['respondida'] = True
                d.save('saida', m)
                try:
                    a = d.book(dict(paciente_id=p['id'], servico=m['servico'], inicio=m['inicio'], profissional=m['profissional'], modalidade=m['modalidade']))
                    return self.booked(a)
                except Error as exc:
                    if exc.status not in (409, 422):
                        raise
                    return 'Esse horário está ocupado ou indisponível.'
        from .nutrition import Nutrition
        nutrition = Nutrition(d)
        words = set(text.split())
        has_number = re.search(r'\d+(?:[.,]\d+)?', text) is not None
        recording = (has_number and bool(words & {'kg', 'quilo', 'quilos', 'peso', 'pesei', 'pesando'})) or 'peso' in words or bool(words & {'copo', 'copos', 'comi', 'fiz', 'tomei', 'feita', 'feito', 'almocei', 'jantei'}) or any(t in text for t in ('pulei', 'pulou', 'nao comi', 'nao fiz', 'nao tomei'))
        if recording:
            return nutrition.chat_record(p, text)
        if any(t in text for t in ('meu plano', 'plano alimentar', 'cardapio', 'dieta', 'posso comer', 'pode comer', 'o que comer', 'o que como')):
            return nutrition.chat_plan(p, text, self, number)
        if 'link' in words:
            appointments = sorted((a for a in d.all('agendamentos') if p and a['paciente_id'] == p['id'] and a['modalidade'] == 'online' and a['status'] in ('agendado', 'confirmado') and a['inicio'] >= now().isoformat(timespec='minutes')), key=lambda a: a['inicio'])
            return (appointments[0]['link'] or 'A equipe vai informar o link.') if appointments else 'Não encontrei uma consulta online futura.'
        if any(t in text for t in ('agendar', 'marcar', 'consulta')):
            state['fluxo'] = 'servico' if p else 'nome'
            return self.prompt(state)
        best, score = None, 0
        for item in d.all('faq'):
            for question in item['perguntas']:
                tokens = significant(question)
                ratio = len(tokens & words) / len(tokens) if tokens else 0
                if ratio >= .6 and ratio > score:
                    best, score = item['resposta'], ratio
        if best is not None:
            return best
        state['nao_entendi'] = misses + 1
        if state['nao_entendi'] >= 2:
            self.human(number, 'nao_entendi')
        return 'Não entendi. Você pode pedir um atendente.'

    def prompt(self, state):
        if state['fluxo'] == 'nome':
            return 'Qual é seu nome?'
        if state['fluxo'] == 'servico':
            state['servicos'] = [s['id'] for s in self.d.all('servicos') if s['ativo']]
            return '\n'.join(f"{i} - {self.d.get('servicos', sid)['nome']}" for i, sid in enumerate(state['servicos'], 1)) or 'Não há serviços disponíveis.'
        if state['fluxo'] == 'modalidade':
            return '1 - Presencial\n2 - Online'
        return '\n'.join(f"{i}) {timestamp(s['inicio']).strftime('%d/%m %H:%M')} com {self.d.get('profissionais', s['profissional'])['nome']}" for i, s in enumerate(state['horarios'], 1)) or 'Não há horários disponíveis nesta janela.'

    def offer(self, state):
        state['fluxo'], state['horarios'] = 'horario', []
        for day in range(self.d.config['janela_dias'] + 1):
            state['horarios'].extend(self.d.slots({'servico': state['servico'], 'data': (now() + timedelta(days=day)).strftime('%Y-%m-%d')}))
            if len(state['horarios']) >= 3:
                break
        state['horarios'] = state['horarios'][:3]
        return self.prompt(state)

    def booked(self, a):
        from .telegram import Telegram
        Telegram(self.d).appointment(a)
        return f"Agendado para {timestamp(a['inicio']).strftime('%d/%m %H:%M')} ({a['modalidade']})."

    def flow(self, number, original, text, state, p):
        if text == 'cancelar':
            state['fluxo'] = None
            return 'Fluxo cancelado.'
        if state['fluxo'] == 'nome':
            _, created = self.d.patient({'nome': original, 'telefone': number})
            state['fluxo'] = 'servico'
            return self.prompt(state)
        choice = int(text) - 1 if text.isdigit() else -1
        if state['fluxo'] == 'servico':
            if choice not in range(len(state['servicos'])):
                return self.prompt(state)
            state['servico'] = state['servicos'][choice]
            return self.offer(state)
        if state['fluxo'] == 'horario':
            if choice not in range(len(state['horarios'])):
                return self.prompt(state)
            state['escolhido'] = state['horarios'][choice]
            if self.d.config['atende_online']:
                state['fluxo'] = 'modalidade'
                return self.prompt(state)
            mode = 'presencial'
        else:
            if choice not in (0, 1):
                return self.prompt(state)
            mode = ('presencial', 'online')[choice]
        try:
            a = self.d.book(dict(state['escolhido'], paciente_id=p['id'], servico=state['servico'], modalidade=mode))
        except Error as exc:
            if exc.status not in (409, 422):
                raise
            return 'Horário ocupado ou indisponível.\n' + self.offer(state)
        state['fluxo'] = None
        return self.booked(a)
