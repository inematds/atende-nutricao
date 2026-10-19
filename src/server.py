"""Servidor HTTP com autenticação prévia e SQLite transacional."""
import argparse
import hmac
import json
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit
from .domain import Domain
from .storage import Error, ROOT, Store


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, status, body):
        data = b'' if status == 204 else json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def static(self, path):
        # Lista fechada: nenhum caminho fornecido pelo visitante vira um arquivo.
        assets = {
            '/': ('index.html', 'text/html'),
            '/equipe': ('equipe.html', 'text/html'),
            '/web/style.css': ('style.css', 'text/css'),
            '/web/chat.js': ('chat.js', 'text/javascript'),
            '/web/equipe.js': ('equipe.js', 'text/javascript'),
        }
        if self.command != 'GET' or path not in assets:
            return False
        name, content_type = assets[path]
        data = (ROOT / 'web' / name).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(data)
        return True

    def handle_request(self):
        route = urlsplit(self.path)
        public = (self.command, route.path) in {
            ('GET', '/'), ('GET', '/equipe'), ('GET', '/api/saude'),
            ('GET', '/api/servicos'), ('GET', '/api/horarios'), ('POST', '/api/mensagens')}
        try:
            if self.static(route.path):
                return
            evolution = self.command == 'POST' and route.path.startswith('/webhook/evolution/')
            telegram = self.command == 'POST' and route.path == '/webhook/telegram'
            if telegram:
                secret = os.environ.get('TELEGRAM_SEGREDO', '')
                supplied = self.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
                if not secret or not hmac.compare_digest(secret.encode(), supplied.encode()):
                    raise Error(401, 'Segredo inválido')
                public = True
            if evolution:
                secret = os.environ.get('WEBHOOK_SEGREDO', '')
                if not secret or not hmac.compare_digest(route.path.encode(), ('/webhook/evolution/' + secret).encode()):
                    raise Error(404, 'Rota inexistente')
                public = True
            if not public and not hmac.compare_digest(self.headers.get('X-Token', '').encode(), self.server.store.config['token'].encode()):
                raise Error(401, 'Token inválido')
            body = {}
            if self.command in ('POST', 'PUT'):
                try:
                    body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))) or b'{}')
                except (ValueError, UnicodeError):
                    raise Error(422, 'JSON inválido')
                if not isinstance(body, dict):
                    raise Error(422, 'JSON deve ser objeto')
            if route.path == '/api/saude' and self.command == 'GET':
                return self.respond(200, {'ok': True, 'versao': (ROOT / 'VERSION').read_text().strip()})
            db = self.server.store.connect()
            try:
                with db:
                    # Reserva a escrita antes de verificar disponibilidade: duas reservas não vencem juntas.
                    db.execute('BEGIN IMMEDIATE')
                    domain = Domain(self.server.store, db)
                    if telegram:
                        from .telegram import Telegram
                        status, result = 200, Telegram(domain).receive(body)
                    elif evolution:
                        from .integrations import Evolution
                        status, result = 200, Evolution(domain).receive(body)
                    else:
                        status, result = domain.route(self.command, route.path, dict(parse_qsl(route.query)), body)
            finally:
                db.close()
            self.respond(status, result)
        except Error as exc:
            self.respond(exc.status, {'erro': exc.message})
        except (ValueError, TypeError):
            self.respond(422, {'erro': 'Dados inválidos'})
        except Exception:
            traceback.print_exc()
            self.respond(500, {'erro': 'Erro interno'})

    do_GET = do_POST = do_PUT = do_DELETE = handle_request


def main():
    parser = argparse.ArgumentParser(description='Atendimento do consultório de nutrição')
    commands = parser.add_subparsers(dest='command', required=True)
    serve = commands.add_parser('serve')
    serve.add_argument('--porta', type=int, default=8080)
    serve.add_argument('--dados', required=True)
    serve.add_argument('--host', default='127.0.0.1')
    report = commands.add_parser('raiox')
    report.add_argument('--dados', required=True)
    report.add_argument('--mes', required=True)
    report.add_argument('--acompanhamento', required=True)
    backup = commands.add_parser('backup')
    backup.add_argument('--dados', required=True)
    backup.add_argument('--saida', required=True)
    restore = commands.add_parser('restaurar')
    restore.add_argument('--dados', required=True)
    restore.add_argument('--entrada', required=True)
    args = parser.parse_args()
    if args.command in ('backup', 'restaurar'):
        from .backup import transfer
        transfer(args.dados, args.saida if args.command == 'backup' else args.entrada,
                 restore=args.command == 'restaurar')
        return
    store = Store(args.dados)
    if args.command == 'raiox':
        from .reporting import Reporting
        db = store.connect()
        try:
            with db:
                db.execute('BEGIN')
                Reporting(Domain(store, db)).export(args.mes, args.acompanhamento)
        finally:
            db.close()
        return
    server = ThreadingHTTPServer((args.host, args.porta), Handler)
    server.store = store
    print(f'PORTA={server.server_address[1]}', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
