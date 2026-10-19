"""Canal da equipe, com referências persistidas e configuração pelo ambiente."""
import json
import os
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, build_opener

from .domain import now, timestamp
from .integrations import NoRedirect
from .storage import Error


class Telegram:
    def __init__(self, domain):
        self.d = domain

    def send(self, text, attendance=None, reply=None):
        env = [os.environ.get(key, '') for key in
               ('TELEGRAM_API_URL', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_SEGREDO')]
        if not all(env):
            return None
        base, token, chat, _ = env
        payload = {'chat_id': chat, 'text': text}
        if reply is not None:
            payload['reply_to_message_id'] = reply
        try:
            req = Request(base.rstrip('/') + '/bot' + quote(token, safe='') + '/sendMessage',
                          data=json.dumps(payload, ensure_ascii=False).encode(),
                          headers={'Content-Type': 'application/json'}, method='POST')
            with build_opener(NoRedirect).open(req, timeout=3) as response:
                result = json.load(response)
            identifier = result.get('result', {}).get('message_id')
            if result.get('ok') and identifier is not None:
                if attendance is not None:
                    self.d.save('telegram_referencias', {'id': identifier, 'atendimento_id': attendance})
                return identifier
        except (URLError, OSError, ValueError, AttributeError):
            pass
        return None

    def forward(self, row, text, opening=False):
        label = row['nome'] or row['telefone']
        if opening:
            message = f"#{row['id']} {label} {row['telefone']} — {row['motivo']}"
            if row['prioridade'] == 'alta':
                message += ' ALTA'
            identifier = self.send(message + '\n' + text, row['id'])
            if identifier is not None:
                row['telegram_message_id'] = identifier
                self.d.save('atendimentos', row)
        else:
            prefix = 'ALTA ' if row['prioridade'] == 'alta' else ''
            self.send(f"#{row['id']} {label}: {prefix}{text}", row['id'], row.get('telegram_message_id'))

    def appointment(self, a, cancelled=False):
        d = self.d
        p = d.get('pacientes', a['paciente_id'])
        service = d.get('servicos', a['servico'])
        professional = d.get('profissionais', a['profissional'])
        prefix = 'Cancelado:' if cancelled else 'Novo agendamento:'
        text = f"{prefix} {timestamp(a['inicio']).strftime('%d/%m %H:%M')} {p['nome']} — {service['nome']} com {professional['nome']}"
        if a['modalidade'] == 'online':
            text += ' (online)'
        self.send(text)

    def receive(self, body):
        message = body.get('message')
        if not isinstance(message, dict):
            return {'ok': True}
        chat = message.get('chat')
        if not isinstance(chat, dict) or str(chat.get('id')) != os.environ.get('TELEGRAM_CHAT_ID', ''):
            return {'ok': True}
        text = message.get('text')
        if not isinstance(text, str) or not text.strip():
            return {'ok': True}
        update = body.get('update_id')
        if update is not None:
            if any(str(r['id']) == str(update) for r in self.d.all('telegram_recebidas')):
                return {'ok': True}
            self.d.save('telegram_recebidas', {'id': update})
        parts = text.split(maxsplit=2)
        command = parts[0]
        try:
            if command in ('/responder', '/encerrar'):
                if len(parts) < 2 or (command == '/responder' and len(parts) < 3):
                    self.send('Informe o atendimento e, para responder, o texto.')
                else:
                    self.d.route('POST', f'/api/atendimento-humano/{parts[1]}/{command[1:]}', {},
                                 {'texto': parts[2]} if command == '/responder' else {})
            elif command in ('/fila', '/alertas'):
                rows = [r for r in self.d.all('atendimentos') if r['status'] == 'aberto'
                        and (command == '/fila' or r['prioridade'] == 'alta')]
                self.send('\n'.join(f"#{r['id']} {r['nome'] or r['telefone']} — {r['motivo']}" for r in rows)
                          or 'Nenhum atendimento aberto.')
            elif command == '/agenda':
                day = parts[1] if len(parts) > 1 else now().strftime('%Y-%m-%d')
                _, result = self.d.route('GET', '/api/agendamentos', {'data': day}, {})
                lines = []
                for a in result['agendamentos']:
                    if a['status'] == 'cancelado':
                        continue
                    service = self.d.get('servicos', a['servico'])['nome']
                    professional = self.d.get('profissionais', a['profissional'])['nome']
                    line = f"{a['inicio'][11:16]} {a['nome']} — {service} ({professional})"
                    lines.append(line + (' [online]' if a['modalidade'] == 'online' else ''))
                self.send('\n'.join(lines) or 'Nenhum agendamento.')
            else:
                reply = message.get('reply_to_message')
                identifier = reply.get('message_id') if isinstance(reply, dict) else None
                ref = next((r for r in self.d.all('telegram_referencias') if r['id'] == identifier), None)
                if ref:
                    self.d.route('POST', f"/api/atendimento-humano/{ref['atendimento_id']}/responder", {}, {'texto': text})
        except Error as exc:
            self.send(exc.message)
        return {'ok': True}
