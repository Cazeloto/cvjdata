from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import streamlit as st
from db import load_data
from visual import shell

st.set_page_config(page_title='CVJ • Indicadores das giras', page_icon='🌿', layout='wide')
shell('Dashboard das giras', 'Público, participação e acompanhamento das atividades', active='geral')

@st.cache_data(ttl=300, show_spinner='Consultando as giras…')
def data():
    return (*load_data(), datetime.now(ZoneInfo('America/Sao_Paulo')))

def number(value):
    return f'{int(value):,}'.replace(',', '.')

def chart(fig):
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      margin=dict(l=10,r=10,t=30,b=10), font=dict(color='#24483f'),
                      legend_title_text='')
    st.plotly_chart(fig, width='stretch')

st.sidebar.title('🌿 CVJ')
st.sidebar.caption('ACOMPANHAMENTO DAS GIRAS')
if st.sidebar.button('Atualizar dados', width='stretch'):
    data.clear()
try:
    records, attendance, updated = data()
except Exception:
    st.error('Não foi possível consultar o Neon. Confira as variáveis NEON_DB no .env e o acesso à rede.')
    st.stop()

st.caption(f'Visão do público e da presença dos médiuns • Atualizado em {updated:%d/%m/%Y às %H:%M}')
if records.empty or records['data'].dropna().empty:
    st.info('Não há registros de giras com data nesta base.')
    st.stop()
today = pd.Timestamp(datetime.now(ZoneInfo('America/Sao_Paulo')).date())
minimum = records['data'].min().date()
maximum = max(records['data'].max().date(), today.date())
start = max(minimum, today.replace(month=1, day=1).date())
end = max(start, today.date())
period = st.sidebar.date_input('Período', (start, end), min_value=minimum, max_value=maximum, format='DD/MM/YYYY')
types = st.sidebar.multiselect('Tipo de gira', sorted(records['tipo'].unique()), placeholder='Todos os tipos')
st.sidebar.caption('Consulta somente leitura. Cache de 5 minutos.')
if len(period) != 2:
    st.info('Selecione a data inicial e a data final.')
    st.stop()
filtered = records[records['data'].between(pd.Timestamp(period[0]), pd.Timestamp(period[1]))].copy()
if types:
    filtered = filtered[filtered['tipo'].isin(types)]
past = filtered[filtered['data'] <= today].copy()
future = filtered[filtered['data'] > today].copy()

public_tab, attendance_tab, schedule_tab = st.tabs(['Panorama do público', 'Presença dos médiuns', 'Agenda e registros'])
with public_tab:
    st.caption('Indicadores abaixo consideram apenas datas até hoje. Uma linha da tabela registros corresponde a um registro de gira.')
    if past.empty:
        st.info('Nenhuma gira passada no período e nos tipos selecionados.')
    else:
        cols = st.columns(4)
        cols[0].metric('Giras registradas', number(len(past)))
        cols[1].metric('Público registrado', number(past['publico'].sum()))
        cols[2].metric('Média por gira', f"{past['publico'].mean():.1f}".replace('.', ',') if past['publico'].notna().any() else '—')
        cols[3].metric('Desistências registradas', number(past['desistencias'].sum()))
        missing = past['publico'].isna().sum()
        zeros = past['publico'].eq(0).sum()
        if zeros or missing:
            st.info(f'{zeros} gira(s) com público zero e {missing} sem valor. Zero pode indicar lançamento pendente; não confirma ausência de público. A média inclui zeros e exclui valores nulos.')
        monthly = past.assign(mes=past['data'].dt.to_period('M').dt.to_timestamp()).groupby('mes',as_index=False)[['publico','desistencias']].sum()
        st.subheader('Evolução mensal')
        chart(px.line(monthly, x='mes', y=['publico','desistencias'], markers=True,
                      labels={'mes':'Mês','value':'Quantidade','variable':'Indicador'},
                      color_discrete_sequence=['#635079','#b695c2']))
        left,right = st.columns(2)
        with left:
            st.subheader('Público por tipo de gira')
            totals=past.groupby('tipo',as_index=False)['publico'].sum().sort_values('publico')
            chart(px.bar(totals,x='publico',y='tipo',orientation='h',labels={'publico':'Público','tipo':''},color_discrete_sequence=['#635079']))
        with right:
            st.subheader('Composição dos registros')
            composition=past[['preferencial','normal','outros']].sum().rename_axis('Categoria').reset_index(name='Quantidade')
            if composition['Quantidade'].sum()>0:
                chart(px.pie(composition,names='Categoria',values='Quantidade',hole=.65,color_discrete_sequence=['#635079','#9470a5','#d5c1de']))
            else:
                st.info('Sem valores de composição no período.')
        mismatch = (past[['preferencial','normal','outros']].sum(axis=1,min_count=3)-past['publico']).dropna().ne(0).sum()
        if mismatch:
            st.warning(f'{mismatch} registro(s) com diferença entre o público e a soma das categorias. O total usa o campo reg_frequencia.')

with attendance_tab:
    st.caption('Dados agregados da tabela giras. Os filtros de período se aplicam aqui; selecione os tipos de presença abaixo, pois esta tabela usa códigos próprios.')
    if types:
        st.info('O filtro de tipo da barra lateral aplica-se ao público e à agenda. Para presença, use o filtro abaixo.')
    att = attendance[attendance['data'].between(pd.Timestamp(period[0]),min(pd.Timestamp(period[1]),today))].copy()
    att_types = st.multiselect('Código do tipo de gira (presença)', sorted(att['tipo'].dropna().unique()))
    if att_types:
        att=att[att['tipo'].isin(att_types)]
    if att.empty:
        st.info('Sem registros de presença no período.')
    else:
        status=att.groupby('situacao',as_index=False)['quantidade'].sum()
        total=att['quantidade'].sum()
        present=att.loc[att['situacao'].eq('P'),'quantidade'].sum()
        a,b,c=st.columns(3)
        a.metric('Marcações P',number(present))
        b.metric('Registros de participação',number(total))
        c.metric('P / total de registros',f'{100*present/total:.1f}%'.replace('.',','))
        st.caption('Cada registro é uma participação de médium em gira, não uma pessoa única. P é tratado como presença; A e D são exibidos como códigos, sem inferir seu significado. Sem marcação não é classificado como falta.')
        chart(px.bar(status,x='situacao',y='quantidade',labels={'situacao':'Marcação','quantidade':'Registros'},color_discrete_sequence=['#635079']))
        st.dataframe(att.rename(columns={'data':'Data','gira':'Gira','tipo':'Código do tipo','situacao':'Marcação','quantidade':'Quantidade'}),hide_index=True,width='stretch')

with schedule_tab:
    st.subheader('Próximas giras no período')
    if future.empty:
        st.info('Nenhuma gira futura no período selecionado. Amplie a data final para consultar a agenda.')
    else:
        st.dataframe(future[['data','descricao','tipo']].rename(columns={'data':'Data','descricao':'Gira','tipo':'Tipo'}),hide_index=True,width='stretch')
    st.subheader('Detalhamento do período')
    display=filtered.rename(columns={'id':'Código','data':'Data','descricao':'Gira','tipo':'Tipo','preferencial':'Preferencial','normal':'Normal','outros':'Outros','publico':'Público','desistencias':'Desistências'}).sort_values('Data',ascending=False)
    st.dataframe(display,hide_index=True,width='stretch')
    st.download_button('Baixar registros em CSV', display.to_csv(index=False,sep=';',date_format='%d/%m/%Y').encode('utf-8-sig'), 'indicadores_giras.csv','text/csv')

with st.expander('Como os indicadores são calculados'):
    st.markdown('''- **Giras registradas:** quantidade de linhas em `registros` dentro do filtro, com data até hoje. Não confirma realização ou encerramento.
- **Público:** soma de `reg_frequencia`; representa participações, não consulentes únicos.
- **Média:** média de `reg_frequencia` por registro, incluindo zeros e excluindo nulos.
- **Desistências:** soma de `reg_desistencia`, apresentada separadamente, sem subtrair do público.
- **Composição:** somas de `reg_preferencial`, `reg_normal` e `reg_outros`.
- **Presença:** contagem das linhas de `giras` agrupadas por data, descrição, tipo e marcação. Não há cruzamento entre as duas tabelas que multiplique os totais.
- Datas futuras ficam fora dos indicadores de público e presença. Horário de referência: São Paulo.''')
