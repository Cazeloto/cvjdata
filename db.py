"""Consultas somente leitura; credenciais permanecem no .env."""
from pathlib import Path
import os
import pandas as pd
import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent

def connect():
    cfg = {**dotenv_values(ROOT / '.env'), **os.environ}
    required = ('HOST', 'NAME', 'USER', 'PASSWORD')
    if any(not cfg.get('NEON_DB_' + key) for key in required):
        raise ValueError('Configuração do Neon incompleta no .env')
    conn = psycopg.connect(
        host=cfg['NEON_DB_HOST'], port=cfg.get('NEON_DB_PORT') or 5432,
        dbname=cfg['NEON_DB_NAME'], user=cfg['NEON_DB_USER'],
        password=cfg['NEON_DB_PASSWORD'],
        sslmode=cfg.get('NEON_DB_SSLMODE') or 'require', connect_timeout=10)
    conn.read_only = True
    return conn

def frame(conn, query):
    cur = conn.execute(query)
    return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])

def load_data():
    with connect() as conn:
        conn.execute("SET LOCAL statement_timeout = '30s'")
        records = frame(conn, '''SELECT reg_codigo AS id, reg_data AS data,
            reg_descricao AS descricao, COALESCE(NULLIF(trim(reg_tipo), ''), 'Sem tipo') AS tipo,
            reg_preferencial AS preferencial, reg_normal AS normal, (to_jsonb(registros)->>'reg_outros')::integer AS outros,
            reg_frequencia AS publico, reg_desistencia AS desistencias
            FROM public.registros ORDER BY reg_data''')
        attendance = frame(conn, '''SELECT gir_data AS data, gir_descricao AS gira,
            trim(gir_tipo) AS tipo, COALESCE(NULLIF(trim(gir_presenca), ''), 'Sem marcação') AS situacao,
            count(*) AS quantidade FROM public.giras GROUP BY 1,2,3,4 ORDER BY 1''')
    for df in (records, attendance):
        df['data'] = pd.to_datetime(df['data'])
    return records, attendance
