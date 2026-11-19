"""Backup consistente do SQLite; deve ser executado no mesmo computador do servidor."""
from pathlib import Path
from datetime import datetime
import sqlite3
from server import app

def main():
    if not app.DB_PATH.is_file():
        raise SystemExit('Banco não existe. Execute a configuração de primeiro acesso.')
    dest=app.ROOT/'backups'
    dest.mkdir(parents=True,exist_ok=True)
    file=dest/('the_end_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.db')
    with sqlite3.connect(app.DB_PATH) as source, sqlite3.connect(file) as target:
        source.backup(target)
        result=target.execute('PRAGMA integrity_check').fetchone()[0]
        if result!='ok':raise RuntimeError('Backup não passou pela verificação de integridade.')
    print('Backup íntegro:',file)
    print('Guarde cópia criptografada em local seguro. O backup contém dados pessoais.')

if __name__=='__main__':main()
