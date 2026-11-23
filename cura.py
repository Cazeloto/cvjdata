"""Histórico completo para evitar falsos abandonos por filtro de período."""
import pandas as pd
from db import connect, frame


def load_cura():
    with connect() as conn:
        conn.execute("SET LOCAL statement_timeout = '30s'")
        return frame(conn, '''SELECT t.tra_codpac AS codigo,
            COALESCE(c.con_nome, 'Cadastro não encontrado') AS nome,
            trim(c.con_status) AS status_cadastro,
            t.tra_data AS data, trim(t.tra_descricao) AS procedimento,
            EXISTS (SELECT 1 FROM public.registros r
                WHERE r.reg_data = t.tra_data AND lower(trim(r.reg_tipo)) = 'cura') AS dia_cura
            FROM public.tratamento t
            LEFT JOIN public.consulente c ON c.con_codigo = t.tra_codpac''')


def load_cura_dates():
    with connect() as conn:
        conn.execute("SET LOCAL statement_timeout = '30s'")
        return frame(conn, '''SELECT DISTINCT reg_data AS data FROM public.registros
            WHERE lower(trim(reg_tipo)) = 'cura' AND reg_data IS NOT NULL''')


def activity_metrics(raw, dates, start, end, reference):
    """Pessoas únicas no período; média usa participações pessoa/data."""
    upper = min(pd.Timestamp(end), pd.Timestamp(reference))
    calendar = pd.to_datetime(dates['data']).drop_duplicates()
    calendar = calendar[calendar.between(pd.Timestamp(start), upper)]
    treatments = raw.assign(data=pd.to_datetime(raw['data']))
    visits = treatments[treatments['data'].isin(calendar)].dropna(subset=['codigo'])
    visits = visits.drop_duplicates(['codigo', 'data'])
    count = len(calendar)
    return {'giras': count, 'consulentes': visits['codigo'].nunique(),
            'participacoes': len(visits), 'media': len(visits) / count if count else None}


def triage_returns(raw, dates, start, end, reference):
    calendar = pd.to_datetime(dates['data']).drop_duplicates().sort_values()
    calendar = calendar[calendar.between(pd.Timestamp(start), min(pd.Timestamp(end), pd.Timestamp(reference)))]
    rows = raw.assign(data=pd.to_datetime(raw['data']))
    rows = rows[rows['data'].isin(calendar)].dropna(subset=['codigo']).copy()
    description = rows['procedimento'].fillna('').str.strip().str.lower()
    rows['triagem'] = description.str.startswith('triagem')
    rows['procedimento_valido'] = description.ne('')
    visits = rows.groupby(['data', 'codigo']).agg(triagem=('triagem', 'any'), valido=('procedimento_valido', 'any')).reset_index()
    visits['categoria'] = 'Sem descrição'
    visits.loc[visits['valido'], 'categoria'] = 'Retorno'
    visits.loc[visits['triagem'], 'categoria'] = 'Triagem'
    counts = visits.groupby(['data', 'categoria']).size().unstack(fill_value=0)
    return counts.reindex(index=pd.DatetimeIndex(calendar), columns=['Triagem', 'Retorno', 'Sem descrição'], fill_value=0).fillna(0).astype(int).rename_axis('data').reset_index()


def summarize(raw, reference, include_triage=False):
    df = raw.copy()
    df['data'] = pd.to_datetime(df['data'])
    valid = df['data'].notna() & df['data'].ne(pd.Timestamp('2000-01-01')) & df['data'].le(pd.Timestamp(reference))
    if not include_triage:
        valid &= ~df['procedimento'].fillna('').str.lower().str.startswith('triagem')
    df = df[valid]
    grouped = df.groupby('codigo', as_index=False).agg(
        nome=('nome', 'first'), status_cadastro=('status_cadastro', 'first'),
        inicio=('data', 'min'), ultimo=('data', 'max'),
        dias=('data', 'nunique'), procedimentos=('data', 'size'))
    first_cure = df[df['dia_cura']].groupby('codigo')['data'].min()
    grouped['primeira_cura'] = grouped['codigo'].map(first_cure)
    # Início deve estar vinculado a uma data de cura; retornos fora dessas datas
    # também contam, para não classificar como abandono quem possui continuidade.
    grouped = grouped[grouped['inicio'].eq(grouped['primeira_cura'])].copy()
    grouped['dias_desde_inicio'] = (pd.Timestamp(reference) - grouped['inicio']).dt.days
    return grouped
