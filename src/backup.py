"""Cópia consistente com SQLite; restauração atômica com servidor parado."""
import os
from pathlib import Path
import sqlite3
import tempfile


def transfer(directory, archive, restore=False):
    database = Path(directory) / 'estado.sqlite3'
    source, destination = (Path(archive), database) if restore else (database, Path(archive))
    if source.resolve() == destination.resolve():
        raise ValueError('Origem e destino devem ser diferentes')
    # mode=ro evita criar um banco vazio quando a origem não existe.
    origin = sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)
    temporary = None
    try:
        if origin.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Banco inválido')
        origin.execute('SELECT documento FROM registros LIMIT 1')
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix='.backup-', dir=destination.parent)
        os.close(descriptor)
        target = sqlite3.connect(temporary)
        try:
            origin.backup(target)
        finally:
            target.close()
        os.replace(temporary, destination)
    finally:
        origin.close()
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
