"""Backup consistente do banco SQLite (gastos-pessoais) com rotação.

- Gera um snapshot íntegro via API de backup do SQLite — seguro mesmo se o app
  estiver escrevendo no banco no mesmo instante.
- Grava em ``backups/`` (dentro do OneDrive → sincroniza para a nuvem sozinho,
  com histórico de versões).
- Mantém apenas os ``MANTER`` snapshots mais recentes.

Uso avulso:  python backup.py
Importável:  from backup import fazer_backup, ultimo_backup
"""
import glob
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'banco.db')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
MANTER = 30  # nº de snapshots a preservar (rotação)


def fazer_backup(db_path: str = DB_PATH, backup_dir: str = BACKUP_DIR,
                 manter: int = MANTER) -> str | None:
    """Cria um snapshot consistente do banco e rotaciona os antigos.

    Retorna o caminho do arquivo criado, ou ``None`` se o banco não existir.
    """
    if not os.path.exists(db_path):
        return None

    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = os.path.join(backup_dir, f'banco_{ts}.db')

    origem = sqlite3.connect(db_path)
    try:
        dest = sqlite3.connect(destino)
        try:
            with dest:
                origem.backup(dest)  # snapshot atômico e íntegro
        finally:
            dest.close()
    finally:
        origem.close()

    _rotacionar(backup_dir, manter)
    return destino


def _rotacionar(backup_dir: str, manter: int) -> None:
    """Remove os snapshots mais antigos, mantendo os ``manter`` mais recentes."""
    if manter <= 0:
        return
    # Nome com timestamp → ordem lexicográfica == ordem cronológica
    arquivos = sorted(glob.glob(os.path.join(backup_dir, 'banco_*.db')))
    for antigo in arquivos[:-manter]:
        try:
            os.remove(antigo)
        except OSError:
            pass


def ultimo_backup(backup_dir: str = BACKUP_DIR):
    """Retorna (caminho, datetime, total) do snapshot mais recente.

    Se não houver nenhum, retorna (None, None, 0).
    """
    arquivos = sorted(glob.glob(os.path.join(backup_dir, 'banco_*.db')))
    if not arquivos:
        return None, None, 0
    mais_recente = arquivos[-1]
    quando = datetime.fromtimestamp(os.path.getmtime(mais_recente))
    return mais_recente, quando, len(arquivos)


if __name__ == '__main__':
    caminho = fazer_backup()
    if caminho:
        print(f'[backup] OK -> {caminho}')
    else:
        print('[backup] banco.db nao encontrado; nada a fazer.')
