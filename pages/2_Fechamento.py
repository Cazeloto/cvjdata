from datetime import datetime
import os
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import streamlit as st
from fechamento import load_fechamento, select_official, match_cure, summarize_closings
from visual import shell, style_chart

st.set_page_config(page_title='CVJ • Fechamento das giras', page_icon='🌿', layout='wide')
shell('Fechamento das giras', 'Consolidação oficial e participação dos consulentes na cura', active='fechamento')

demo = os.environ.get('CVJDATA_DEMO') == '1'
@st.cache_data(ttl=300)
def data(use_demo=False):
    if use_demo:
        from massa_teste import generate
        return (*generate(), datetime.now(ZoneInfo('America/Sao_Paulo')))
    return (*load_fechamento(), datetime.now(ZoneInfo('America/Sao_Paulo')))

if st.sidebar.button('Atualizar fechamentos', width='stretch'):
    data.clear()
try:
    calendar, closing, cure, updated = data(demo)
except Exception:
    st.error('Não foi possível consultar os fechamentos. Verifique a conexão e a tabela fechamento_gira.')
    st.stop()
today = pd.Timestamp(datetime.now(ZoneInfo('America/Sao_Paulo')).date())
if demo:
    today = pd.Timestamp('2026-11-23')
    st.warning('MODO DE TESTE — dados fictícios, sem consulta ao banco nesta página. Data de referência: 23/11/2026.')
st.caption(f'Atualizado em {updated:%d/%m/%Y às %H:%M} • Consulta somente leitura')
period = st.sidebar.date_input('Período dos fechamentos', (today.replace(month=1, day=1).date(), today.date()), format='DD/MM/YYYY')
types = st.sidebar.multiselect('Tipo de gira oficial', sorted(calendar['tipo'].dropna().unique()))
scope = st.sidebar.radio('Participação na cura', ['No mesmo período', 'Em todo o histórico até hoje'])
if len(period) != 2:
    st.info('Selecione o início e o fim do período.')
    st.stop()
selected = select_official(calendar, closing, *period, today, types)
outside = closing[closing['data'].between(pd.Timestamp(period[0]), min(pd.Timestamp(period[1]), today)) & ~closing['data'].isin(calendar['data'])]
if not outside.empty:
    st.info(f'{len(outside)} registro(s) em {outside["data"].nunique()} data(s) fora do calendário oficial foram excluídos dos indicadores.')
    with st.expander('Datas excluídas'):
        st.dataframe(outside.groupby('data').size().rename('Registros excluídos').reset_index(), hide_index=True)
general, by_gira, overlap = st.tabs(['Consolidado das giras', 'Por gira fechada', 'Consulentes que também participam da cura'])
with by_gira:
    st.subheader('Números por gira fechada')
    st.caption('Normais incluem a fila de espera. Não apareceu é contado separadamente. Os números representam registros de senhas, sem acompanhantes.')
    if selected.empty:
        st.info('Não há giras oficiais com fechamento no período selecionado.')
    else:
        summary = summarize_closings(selected)
        day = st.selectbox('Selecione a gira fechada', summary['data'].sort_values(ascending=False).tolist(),
            format_func=lambda d: f'{d:%d/%m/%Y} — {summary.loc[summary["data"].eq(d), "gira"].iloc[0]}')
        row = summary.loc[summary['data'].eq(day)].iloc[0]
        a, b, c = st.columns(3)
        a.metric('Normais + acompanhantes', int(row['normais'] + row['acompanhantes_normais']))
        b.metric('Preferenciais + acompanhantes', int(row['preferenciais'] + row['acompanhantes_preferenciais']))
        c.metric('Desistiu + acompanhante', int(row['nao_apareceu'] + row['acompanhantes_nao_apareceu']))
        st.caption(f'Dos normais, {int(row["espera"])} são senhas da fila de espera. Acompanhantes: {int(row["acompanhantes_normais"])} nos normais e {int(row["acompanhantes_preferenciais"])} nos preferenciais. Total de registros da gira: {int(row["registros"])}.')
        if row['sem_classificacao']:
            st.warning(f'{int(row["sem_classificacao"])} registro(s) sem classificação de fila.')
        display = summary.copy()
        display = summary[['data', 'tipo', 'gira']].copy()
        display['Normal+A'] = summary['normais'] + summary['acompanhantes_normais']
        display['Preferencial+A'] = summary['preferenciais'] + summary['acompanhantes_preferenciais']
        display['Desistiu+A'] = summary['nao_apareceu'] + summary['acompanhantes_nao_apareceu']
        labels = ['Normal+A', 'Preferencial+A', 'Desistiu+A']
        values = pd.DataFrame({'Categoria':labels, 'Quantidade':[int(row['normais']+row['acompanhantes_normais']), int(row['preferenciais']+row['acompanhantes_preferenciais']), int(row['nao_apareceu']+row['acompanhantes_nao_apareceu'])]})
        st.plotly_chart(style_chart(px.bar(values, x='Categoria', y='Quantidade', color='Categoria',
            color_discrete_sequence=['#635079','#b695c2','#c77768'])), width='stretch')
        st.subheader('Comparação das giras fechadas')
        display = display.rename(columns={'data':'Data', 'tipo':'Tipo', 'gira':'Gira'})
        display['Data'] = pd.to_datetime(display['Data']).dt.strftime('%d/%m/%Y')
        st.plotly_chart(style_chart(px.bar(display, x='Data', y=labels, barmode='group',
            labels={'value':'Registros', 'variable':'Categoria'}, color_discrete_sequence=['#635079','#b695c2','#c77768'])), width='stretch')
        st.dataframe(display, hide_index=True, width='stretch')
        st.download_button('Baixar números por gira CSV', display.to_csv(index=False, sep=';', date_format='%d/%m/%Y').encode('utf-8-sig'), 'numeros_por_gira.csv', 'text/csv')
    st.caption('Classificação pelo prefixo da senha (N-, E-, P- ou A-), pois o fechamento armazena E e A como fila N. Quando não existe prefixo reconhecido, usa o campo fila. Esses registros não confirmam atendimento concluído.')
with general:
    cols = st.columns(4)
    cols[0].metric('Giras com fechamento', selected['data'].nunique())
    cols[1].metric('Registros de consulentes', len(selected))
    cols[2].metric('Acompanhantes informados', int(selected['acompanhantes'].sum()))
    cols[3].metric('Nomes únicos', selected.loc[selected['chave'].ne(''), 'chave'].nunique())
    st.caption('Cada linha do fechamento conta como um registro de consulente. Acompanhantes são contabilizados separadamente; não possuem nomes para o cruzamento.')
    if selected.empty:
        st.info('Ainda não há fechamentos em datas oficiais para os filtros selecionados.')
    else:
        daily = selected.groupby(['data', 'tipo', 'gira'], as_index=False).agg(
            registros=('id', 'size'), acompanhantes=('acompanhantes', lambda s: s.sum(min_count=1)))
        st.plotly_chart(style_chart(px.bar(daily, x='data', y='registros', color='tipo', labels={'data':'Data', 'registros':'Consulentes', 'tipo':'Tipo'})), width='stretch')
        left, right = st.columns(2)
        with left:
            counts = selected.assign(fila=selected['fila'].fillna('Sem fila')).groupby('fila').size().reset_index(name='Registros')
            st.plotly_chart(style_chart(px.pie(counts, names='fila', values='Registros', hole=.6)), width='stretch')
        with right:
            counts = selected.assign(medium=selected['medium'].fillna('').str.strip().replace('', 'Não informado')).groupby('medium').size().reset_index(name='Registros')
            st.plotly_chart(style_chart(px.bar(counts, x='Registros', y='medium', labels={'medium':'Médium'}, orientation='h')), width='stretch')
        st.subheader('Consolidado por gira')
        display = daily.rename(columns={'data':'Data', 'tipo':'Tipo', 'gira':'Gira', 'registros':'Consulentes', 'acompanhantes':'Acompanhantes'})
        st.dataframe(display, hide_index=True, width='stretch')
        st.download_button('Baixar consolidado CSV', display.to_csv(index=False, sep=';', date_format='%d/%m/%Y').encode('utf-8-sig'), 'fechamento_giras.csv', 'text/csv')
        if selected['acompanhantes'].isna().any():
            st.caption('Há registros sem quantidade de acompanhantes; o total soma somente os valores informados.')
with overlap:
    people = match_cure(selected, cure, *period, today, same_period=scope == 'No mesmo período')
    total, shared = len(people), int(people['tambem_cura'].sum())
    a,b,c = st.columns(3)
    a.metric('Nomes únicos nas giras', total)
    b.metric('Também participam da cura', shared)
    c.metric('Percentual com participação na cura', f'{100*shared/total:.1f}%' if total else '—')
    st.caption(f'Cura: {scope.lower()}. Considera atendimento registrado em data oficial de cura, incluindo triagem. O cadastro sozinho não indica participação.')
    if not total:
        st.info('Sem consulentes com nome em fechamentos oficiais para realizar o cruzamento.')
    else:
        st.plotly_chart(style_chart(px.pie(names=['Também na cura', 'Sem correspondência na cura'], values=[shared,total-shared], hole=.65, color_discrete_sequence=['#635079','#d5c1de'])), width='stretch')
        per_day = selected[selected['chave'].ne('')][['data','chave']].drop_duplicates()
        per_day['na_cura'] = per_day['chave'].isin(people.loc[people['tambem_cura'], 'chave'])
        trend = per_day.groupby('data', as_index=False).agg(nomes=('chave','size'), tambem_cura=('na_cura','sum'))
        st.plotly_chart(style_chart(px.bar(trend, x='data', y=['nomes','tambem_cura'], barmode='group', labels={'data':'Data da gira','value':'Nomes únicos','variable':'Indicador'})), width='stretch')
        only = st.checkbox('Exibir somente quem também participa da cura', value=True)
        search = st.text_input('Pesquisar nome')
        display = people[people['tambem_cura']] if only else people
        if search:
            from fechamento import normalize_name
            display = display[display['chave'].str.contains(normalize_name(search), regex=False)]
        display = display.drop(columns='chave').rename(columns={'nome':'Nome','giras':'Giras no período','dias_cura':'Dias de cura','primeira_cura':'Primeira cura no recorte','ultima_cura':'Última cura no recorte','cadastros_cura':'Cadastros com o mesmo nome','tambem_cura':'Também na cura'})
        st.dataframe(display, hide_index=True, width='stretch')
        st.download_button('Baixar cruzamento CSV', display.to_csv(index=False, sep=';', date_format='%d/%m/%Y').encode('utf-8-sig'), 'giras_e_cura.csv', 'text/csv')
    st.caption(f'{selected["chave"].eq("").sum()} registro(s) sem nome excluídos do cruzamento. Homônimos podem representar pessoas diferentes; nomes diferentes ou abreviados não são associados automaticamente.')
with st.expander('Critérios dos indicadores'):
    st.markdown('''- Data oficial: data presente no calendário `registros`. Datas futuras e datas fora desse calendário não entram nos indicadores.
- Somente datas com fechamento entram na quantidade de giras; múltiplas entradas do calendário na mesma data não multiplicam os registros.
- O cruzamento usa o nome completo, ignorando acentos, maiúsculas e espaços repetidos. Cada nome conta uma vez no total, mesmo com várias giras ou procedimentos.
- A cura exige registro em `tratamento`, ligado a `consulente`, em data de `registros` cujo tipo é Cura. A data sentinela 01/01/2000 é excluída.
- O percentual divide nomes encontrados na cura pelos nomes válidos dos fechamentos selecionados. A comparação indica participação nas duas atividades, sem inferir encaminhamento ou ordem temporal.''')
