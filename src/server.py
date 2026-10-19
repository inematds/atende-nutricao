"""Servidor HTTP com autenticação prévia e SQLite transacional."""
import argparse
import hmac
import json
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

    def handle_request(self):
        route = urlsplit(self.path)
        public = (self.command, route.path) in {
            ('GET', '/'), ('GET', '/equipe'), ('GET', '/api/saude'),
            ('GET', '/api/servicos'), ('GET', '/api/horarios'), ('POST', '/api/mensagens')}
        try:
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
                    status, result = Domain(self.server.store, db).route(self.command, route.path, dict(parse_qsl(route.query)), body)
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
    args = parser.parse_args()
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
