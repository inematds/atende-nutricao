"""Estado persistente; uma transação por operação HTTP."""
import json
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class Error(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        config = self.directory / 'nutricao.json'
        if not config.exists():
            shutil.copyfile(ROOT / 'exemplos/nutricao.json', config)
        self.config = json.loads(config.read_text())
        self.path = self.directory / 'estado.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS registros (colecao TEXT, id TEXT, documento TEXT NOT NULL, PRIMARY KEY (colecao,id))')
            if not db.execute("SELECT 1 FROM registros WHERE colecao='sistema' AND id='semente'").fetchone():
                for collection in ('servicos', 'profissionais', 'faq'):
                    for entry in self.config.get(collection, []):
                        entry = dict(entry)
                        if collection != 'faq':
                            entry['ativo'] = True
                        if collection == 'profissionais':
                            entry.setdefault('registro', None)
                            entry.setdefault('horarios', None)
                        self.save(db, collection, entry)
                self.save(db, 'sistema', {'id': 'semente'})

    def connect(self):
        return sqlite3.connect(self.path, timeout=20)

    def all(self, db, collection):
        return [json.loads(row[0]) for row in db.execute(
            'SELECT documento FROM registros WHERE colecao=? ORDER BY rowid', (collection,))]

    def get(self, db, collection, key):
        row = db.execute('SELECT documento FROM registros WHERE colecao=? AND id=?', (collection, str(key))).fetchone()
        if row is None:
            raise Error(404, 'Registro inexistente')
        return json.loads(row[0])

    def save(self, db, collection, entry):
        if 'id' not in entry:
            row = db.execute('SELECT MAX(CAST(id AS INTEGER)) FROM registros WHERE colecao=?', (collection,)).fetchone()
            entry['id'] = (row[0] or 0) + 1
        db.execute('INSERT INTO registros VALUES (?,?,?) ON CONFLICT(colecao,id) DO UPDATE SET documento=excluded.documento',
                   (collection, str(entry['id']), json.dumps(entry, ensure_ascii=False)))
        return entry
