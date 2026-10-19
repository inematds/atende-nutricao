"""Transporte configurado exclusivamente pelo ambiente e entrada de metadados."""
import json
import os
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .domain import now, phone
from .storage import Error


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def send_whatsapp(number, text):
    base = os.environ.get('EVOLUTION_URL', '')
    if not base:
        return 'simulado'
    instance = quote(os.environ.get('EVOLUTION_INSTANCIA', ''), safe='')
    payload = json.dumps({'number': number.lstrip('+'), 'text': text}, ensure_ascii=False).encode()
    try:
        request = Request(base.rstrip('/') + '/message/sendText/' + instance, data=payload,
                          headers={'Content-Type': 'application/json',
                                   'apikey': os.environ.get('EVOLUTION_API_KEY', '')}, method='POST')
        with build_opener(NoRedirect).open(request, timeout=3) as response:
            return 'enviado' if 200 <= response.status < 300 else 'pendente'
    except (URLError, OSError, ValueError):
        return 'pendente'


class Evolution:
    def __init__(self, domain):
        self.d = domain

    def receive(self, body):
        d = self.d
        data = body.get('data')
        if body.get('event') != 'messages.upsert' or not isinstance(data, dict):
            return {'ok': True}
        key = data.get('key') or {}
        if not isinstance(key, dict):
            return {'ok': True}
        jid = key.get('remoteJid', '')
        identifier = key.get('id')
        if not isinstance(key, dict) or not isinstance(jid, str) or key.get('fromMe') or jid.endswith('@g.us') or not identifier:
            return {'ok': True}
        if any(m['id'] == identifier for m in d.all('evolution_recebidas')):
            return {'ok': True}
        try:
            number = phone(jid.split('@')[0])
        except Error:
            return {'ok': True}
        message = data.get('message') or {}
        if not isinstance(message, dict):
            return {'ok': True}
        d.save('evolution_recebidas', {'id': identifier})
        if 'imageMessage' in message or data.get('messageType') == 'imageMessage':
            photo = message.get('imageMessage') or {}
            photo = photo if isinstance(photo, dict) else {}
            # Somente estes campos entram no diário; nenhum endereço de mídia é usado.
            mime = photo.get('mimetype') if isinstance(photo.get('mimetype'), str) else None
            caption = photo.get('caption') if isinstance(photo.get('caption'), str) else None
            p = next((p for p in d.all('pacientes') if p['telefone'] == number), None)
            if p:
                from .nutrition import Nutrition
                Nutrition(d).record(p['id'], 'foto', mimetype=mime, caption=caption,
                                    message_id=identifier, origem='whatsapp')
                responses = ['Foto registrada no diário.']
            else:
                responses = ['É necessário um cadastro para registrar a foto.']
            self.history(number, caption or '[foto]', responses)
        else:
            extended = message.get('extendedTextMessage') or {}
            text = message.get('conversation') or (extended.get('text') if isinstance(extended, dict) else None)
            if isinstance(text, str) and text:
                from .conversation import Conversation
                responses = Conversation(d).message({'telefone': number, 'texto': text})['respostas']
            else:
                responses = ['Por enquanto só consigo ler mensagens de texto e fotos.']
                self.history(number, '[mensagem sem texto]', responses)
        for response in responses:
            send_whatsapp(number, response)
        return {'ok': True}

    def history(self, number, original, responses):
        for direction, text in [('entrada', original)] + [('saida', r) for r in responses]:
            self.d.save('mensagens', dict(telefone=number, direcao=direction, texto=text,
                                         quando=now().isoformat(timespec='minutes')))
