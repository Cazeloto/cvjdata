"""Fechamentos oficiais e correspondência nominal com a cura."""
import unicodedata
import pandas as pd
from db import connect, frame


def normalize_name(value):
    if pd.isna(value):
        return ''
    text = unicodedata.normalize('NFKD', str(value))
    return ' '.join(''.join(c for c in text if not unicodedata.combining(c)).casefold().split())


def summarize_closings(closing):
    """A exportação converte E/A para N; o prefixo da senha preserva a fila."""
    rows = closing.copy()
    prefix = rows['senha'].fillna('').str.strip().str.upper().str.extract(r'^([NPEA])-', expand=False)
    queue = prefix.fillna(rows['fila'].fillna('').str.strip().str.upper())
    rows['normais'] = queue.isin(['N', 'E']).astype(int)
    rows['preferenciais'] = queue.eq('P').astype(int)
    rows['nao_apareceu'] = queue.eq('A').astype(int)
    rows['espera'] = queue.eq('E').astype(int)
    rows['sem_classificacao'] = (~queue.isin(['N', 'E', 'P', 'A'])).astype(int)
    rows['acompanhantes_normais'] = rows['acompanhantes'].fillna(0).where(queue.isin(['N', 'E']), 0)
    rows['acompanhantes_preferenciais'] = rows['acompanhantes'].fillna(0).where(queue.eq('P'), 0)
    rows['acompanhantes_nao_apareceu'] = rows['acompanhantes'].fillna(0).where(queue.eq('A'), 0)
    return rows.groupby(['data', 'tipo', 'gira'], as_index=False).agg(
        normais=('normais', 'sum'), preferenciais=('preferenciais', 'sum'),
        nao_apareceu=('nao_apareceu', 'sum'), espera=('espera', 'sum'),
        acompanhantes_normais=('acompanhantes_normais', 'sum'),
        acompanhantes_preferenciais=('acompanhantes_preferenciais', 'sum'),
        acompanhantes_nao_apareceu=('acompanhantes_nao_apareceu', 'sum'),
        sem_classificacao=('sem_classificacao', 'sum'), registros=('id', 'size'))


def load_fechamento():
    with connect() as conn:
        conn.execute("SET LOCAL statement_timeout = '30s'")
        calendar = frame(conn, """SELECT reg_data AS data,
            string_agg(DISTINCT trim(reg_tipo), ', ' ORDER BY trim(reg_tipo)) AS tipo,
            string_agg(DISTINCT trim(reg_descricao), ' / ') AS gira
            FROM registros WHERE reg_data IS NOT NULL GROUP BY reg_data""")
        closing = frame(conn, """SELECT id, data_gira AS data, senha, fila, nome,
            acompanhantes, medium FROM fechamento_gira""")
        cure = frame(conn, """SELECT DISTINCT c.con_codigo AS codigo, c.con_nome AS nome,
            t.tra_data AS data FROM tratamento t
            JOIN consulente c ON c.con_codigo = t.tra_codpac
            WHERE EXISTS (SELECT 1 FROM registros r WHERE r.reg_data = t.tra_data
                AND lower(trim(r.reg_tipo)) = 'cura')""")
    for df in (calendar, closing, cure):
        df['data'] = pd.to_datetime(df['data'])
    for df in (closing, cure):
        df['chave'] = df['nome'].map(normalize_name)
    return calendar, closing, cure


def select_official(calendar, closing, start, end, reference, types=()):
    dates = calendar[calendar['data'].between(pd.Timestamp(start), min(pd.Timestamp(end), pd.Timestamp(reference)))]
    if types:
        dates = dates[dates['tipo'].isin(types)]
    return closing.merge(dates, on='data', how='inner', validate='many_to_one')


def match_cure(closing, cure, start, end, reference, same_period=True):
    upper = min(pd.Timestamp(end), pd.Timestamp(reference)) if same_period else pd.Timestamp(reference)
    valid = cure['data'].le(upper) & cure['data'].ne(pd.Timestamp('2000-01-01')) & cure['chave'].ne('')
    if same_period:
        valid &= cure['data'].ge(pd.Timestamp(start))
    visits = cure[valid]
    history = visits.groupby('chave').agg(dias_cura=('data', 'nunique'),
        primeira_cura=('data', 'min'), ultima_cura=('data', 'max'), cadastros_cura=('codigo', 'nunique'))
    people = closing[closing['chave'].ne('')].groupby('chave').agg(
        nome=('nome', 'first'), giras=('data', 'nunique')).join(history)
    people['tambem_cura'] = people['dias_cura'].notna()
    people[['dias_cura', 'cadastros_cura']] = people[['dias_cura', 'cadastros_cura']].fillna(0).astype(int)
    return people.reset_index()
