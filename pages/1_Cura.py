from datetime import datetime
from functools import partial
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import streamlit as st
from cura import load_cura, load_cura_dates, activity_metrics, summarize, triage_returns
from visual import shell, panel_title, style_chart
from pdf_cura import build_pdf

st.set_page_config(page_title='CVJ • Continuidade na cura', page_icon='🌿', layout='wide')
shell('Dashboard das giras de cura', 'Início do tratamento, continuidade e possíveis abandonos')

@st.cache_data(ttl=300, show_spinner='Analisando o histórico de tratamentos…')
def data():
    return load_cura(), load_cura_dates()

if st.sidebar.button('Atualizar dados', width='stretch'):
    data.clear()
try:
    raw, cure_dates = data()
except Exception:
    st.error('Não foi possível consultar os tratamentos no Neon. Confira as variáveis NEON_DB no .env e o acesso à rede.')
    st.stop()

today = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
criterion = st.sidebar.radio('Considerar apenas um…', ['Dia de atendimento', 'Procedimento registrado'])
include_triage = st.sidebar.checkbox('Incluir triagem na contagem', value=False)
days = st.sidebar.number_input('Dias mínimos sem retorno', min_value=0, max_value=3650, value=30, step=1,
    help='Prazo operacional ajustável. Não é uma confirmação de abandono.')
people = summarize(raw, today, include_triage)
valid_dates = pd.to_datetime(cure_dates['data'])
valid_dates = valid_dates[valid_dates.le(pd.Timestamp(today))]
if valid_dates.empty:
    st.info('Nenhuma gira de cura com data até hoje foi identificada.')
    st.stop()
period = st.sidebar.date_input('Período de análise',
    (valid_dates.min().date(), today), min_value=valid_dates.min().date(), max_value=today, format='DD/MM/YYYY')
st.sidebar.caption('Consulta somente leitura • Atualização a cada 5 minutos')
if len(period) != 2:
    st.info('Selecione o início e o fim do período.')
    st.stop()
activity = activity_metrics(raw, cure_dates, period[0], period[1], today)
with st.container(border=True):
    panel_title('ATENDIMENTOS NAS GIRAS DE CURA', f'{period[0]:%d/%m/%Y} a {period[1]:%d/%m/%Y}')
    gira_col, visits_col, people_col, average_col = st.columns(4)
    gira_col.metric('Giras de cura no período', activity['giras'])
    visits_col.metric('Participações no período', activity['participacoes'], help='Cada consulente conta uma vez por data de gira, mesmo com vários procedimentos.')
    people_col.metric('Consulentes atendidos', activity['consulentes'], help='Pessoas distintas com registro datado em uma gira de cura no período, incluindo triagem.')
    average_col.metric('Média de consulentes por gira', f"{activity['media']:.1f}".replace('.', ',') if activity['media'] is not None else '—')
    st.caption(f"{activity['participacoes']} participações no período: cada consulente conta uma vez por data, mesmo com vários procedimentos. A média divide essas participações pelas {activity['giras']} datas de cura cadastradas, incluindo datas sem atendimento registrado. Consulentes atendidos são pessoas únicas no período; triagens estão incluídas.")
pdf_charts = {}
by_gira = triage_returns(raw, cure_dates, period[0], period[1], today)
with st.container(border=True):
    panel_title('TRIAGEM × RETORNO POR GIRA')
    st.caption('Uma pessoa por data. Triagem tem prioridade quando há triagem e procedimento no mesmo dia. Retorno = procedimento registrado sem triagem nessa data; não comprova atendimento anterior. Os filtros de abandono e de inclusão de triagem não alteram este gráfico.')
    if by_gira.empty:
        st.info('Nenhuma gira de cura no período selecionado.')
    else:
        categories = ['Triagem', 'Retorno']
        if by_gira['Sem descrição'].sum():
            categories.append('Sem descrição')
        plot = by_gira.assign(Gira=by_gira['data'].dt.strftime('%d/%m/%Y'))
        fig = px.bar(plot, x='Gira', y=categories, barmode='group',
            labels={'value':'Consulentes', 'variable':'Atendimento'},
            color_discrete_map={'Triagem':'#b695c2','Retorno':'#514466','Sem descrição':'#9ca3af'})
        fig.update_layout(xaxis=dict(type='category', tickangle=-45), legend=dict(orientation='h', y=1.15))
        fig.update_yaxes(dtick=1 if by_gira[categories].to_numpy().max() < 10 else None)
        st.plotly_chart(style_chart(fig, 380), width='stretch')
        pdf_charts['triagem'] = fig
        st.caption(f"No período: {by_gira['Triagem'].sum()} triagens e {by_gira['Retorno'].sum()} retornos. Datas sem registros aparecem com zero.")
        with st.expander('Ver quantidades por gira'):
            st.dataframe(by_gira.rename(columns={'data':'Data'}), hide_index=True, width='stretch', column_config={'Data':st.column_config.DateColumn(format='DD/MM/YYYY')})
st.caption('Na análise de continuidade abaixo, o mesmo período filtra o início do tratamento. Os filtros de triagem e abandono se aplicam apenas a essa análise.')
cohort = people[people['inicio'].between(pd.Timestamp(period[0]), pd.Timestamp(period[1]))].copy()
column = 'dias' if criterion == 'Dia de atendimento' else 'procedimentos'
cohort['unico'] = cohort[column].eq(1)
cohort['possivel_abandono'] = cohort['unico'] & cohort['dias_desde_inicio'].ge(days)
cohort['classificacao'] = 'Mais de um registro no critério'
cohort.loc[cohort['unico'],'classificacao'] = 'Único atendimento recente'
cohort.loc[cohort['possivel_abandono'],'classificacao'] = 'Possível abandono'

st.info(f'Critério atual: um único {"dia de atendimento" if column == "dias" else "procedimento"} no histórico, com pelo menos {days} dias desde o início. Retornos até hoje são verificados mesmo fora do período selecionado.')
a,b,c,d = st.columns(4)
a.metric('Pessoas que iniciaram', len(cohort))
b.metric('Com apenas um atendimento', int(cohort['unico'].sum()))
c.metric('Possível abandono', int(cohort['possivel_abandono'].sum()))
eligible = cohort['dias_desde_inicio'].ge(days).sum()
d.metric('Possível abandono / elegíveis', f"{cohort['possivel_abandono'].sum()/eligible:.1%}".replace('.',',') if eligible else '—')
st.caption(f'A taxa considera {eligible} pessoa(s) que iniciaram há pelo menos {days} dias. Os casos mais recentes ficam fora do denominador.')

if cohort.empty:
    st.info('Não há pessoas com início no período selecionado.')
else:
    continued = int((~cohort['unico']).sum())
    recent = int((cohort['unico'] & ~cohort['possivel_abandono']).sum())
    abandoned = int(cohort['possivel_abandono'].sum())
    left, middle, right = st.columns(3)
    with left, st.container(border=True, key='follow'):
        panel_title('ACOMPANHAMENTO', f'{len(cohort)} pessoas')
        for label, value, color in [('Iniciaram', len(cohort), '#514466'), ('Mais de um', continued, '#9470a5'), ('Apenas um', int(cohort['unico'].sum()), '#b695c2'), ('Possível abandono', abandoned, '#855269')]:
            width = 100 * value / max(len(cohort), 1)
            st.markdown(f'<div class="flow-row"><div class="flow-label">{label}</div><div class="flow-track"><div class="flow-fill" style="width:{width}%;background:{color}"></div></div><b>{value}</b></div>', unsafe_allow_html=True)
    with middle, st.container(border=True, key='distribution'):
        panel_title('CONTINUIDADE DO TRATAMENTO')
        distribution = pd.DataFrame({'Situação':['Mais de um','Único recente','Possível abandono'], 'Pessoas':[continued,recent,abandoned]})
        fig = px.pie(distribution, names='Situação', values='Pessoas', hole=.7, color_discrete_sequence=['#514466','#9470a5','#b695c2'])
        fig.update_traces(textinfo='none')
        fig.update_layout(annotations=[dict(text=f'<b>{len(cohort)}</b><br>pessoas', x=.5, y=.5, showarrow=False, font_size=20)], legend=dict(orientation='h', y=-.1))
        st.plotly_chart(style_chart(fig, 260), width='stretch')
        pdf_charts['distribuicao'] = fig
    with right, st.container(border=True, key='situation'):
        panel_title('SITUAÇÃO DO ACOMPANHAMENTO')
        st.markdown(f'<div class="status-grid"><div class="status-box" style="color:#2462a4;background:#edf3fb"><small>MAIS DE UM</small><b>{continued}</b><small>No critério</small></div><div class="status-box" style="color:#ac6904;background:#fff6e7"><small>RECENTES</small><b>{recent}</b><small>Abaixo do prazo</small></div><div class="status-box" style="color:#b7362e;background:#fff0ee"><small>ATENÇÃO</small><b>{abandoned}</b><small>Possível abandono</small></div></div>', unsafe_allow_html=True)
        st.caption(f'Prazo de acompanhamento: {days} dias. A classificação não confirma abandono.')
    monthly = cohort.assign(mes=cohort['inicio'].dt.to_period('M').dt.to_timestamp()).groupby(['mes','classificacao']).size().reset_index(name='Pessoas')
    figure = px.bar(monthly, x='mes', y='Pessoas', color='classificacao',
        labels={'mes':'Mês de início','classificacao':'Situação'},
        color_discrete_map={'Possível abandono':'#b695c2','Único atendimento recente':'#9470a5','Mais de um registro no critério':'#514466'})
    figure.update_layout(legend_title_text='', margin=dict(t=20,b=10))
    with st.container(border=True, key='evolution'):
        panel_title('EVOLUÇÃO POR MÊS DE INÍCIO')
        st.plotly_chart(style_chart(figure, 320), width='stretch')
        pdf_charts['evolucao'] = figure

with st.container(border=True, key='details'):
    st.subheader('Quem possui apenas um atendimento')
    only_old = st.checkbox('Mostrar somente possíveis abandonos', value=True)
    result = cohort[cohort['possivel_abandono'] if only_old else cohort['unico']].copy()
    search = st.text_input('Buscar por nome ou código')
    if search.strip():
        result = result[result['nome'].str.contains(search.strip(),case=False,regex=False,na=False) | result['codigo'].astype(str).eq(search.strip())]
    result = result.sort_values(['inicio','nome'])
    display = result[['codigo','nome','inicio','ultimo','dias','procedimentos','dias_desde_inicio','status_cadastro','classificacao']].rename(columns={
        'codigo':'Código','nome':'Nome','inicio':'Primeiro atendimento','ultimo':'Último atendimento',
        'dias':'Dias de atendimento','procedimentos':'Procedimentos','dias_desde_inicio':'Dias desde o início',
        'status_cadastro':'Status cadastral (código)','classificacao':'Classificação'})
    st.dataframe(display, hide_index=True, width='stretch', column_config={
        'Primeiro atendimento': st.column_config.DateColumn(format='DD/MM/YYYY'),
        'Último atendimento': st.column_config.DateColumn(format='DD/MM/YYYY')})
    st.caption(f'{len(display)} pessoa(s) na lista. O status cadastral é exibido sem interpretar os códigos A, D ou F.')
    st.download_button('Baixar lista em CSV',display.to_csv(index=False,sep=';',date_format='%d/%m/%Y').encode('utf-8-sig'),
        'cura_possivel_abandono.csv','text/csv')
    st.download_button('Baixar PDF do painel atual',
        data=partial(build_pdf, activity.copy(), cohort.copy(), display.copy(), tuple(period), criterion, include_triage, days, only_old, search, by_gira=by_gira.copy(), charts={key: fig.__class__(fig) for key, fig in pdf_charts.items()}),
        file_name=f'cura_{period[0]:%Y%m%d}_{period[1]:%Y%m%d}.pdf', mime='application/pdf',
        help='Exporta os indicadores, gráficos e toda a lista filtrada com as opções selecionadas no momento.',
        on_click='ignore')

with st.expander('Regras e qualidade dos dados'):
    st.markdown('''- O início é a primeira data válida no histórico disponível de `tratamento`, conforme a opção de incluir triagem. Não identifica reinícios de novos ciclos.
- Essa data precisa coincidir com uma gira do tipo **Cura** em `registros`. A vinculação é por data, pois não há identificador direto da gira no tratamento.
- Todos os retornos com data válida até hoje contam, inclusive em datas sem gira de cura cadastrada e fora do filtro de início.
- Por padrão, vários procedimentos no mesmo dia contam como um atendimento. É possível trocar para exatamente um procedimento.
- Triagem é excluída por padrão. Registros sem data, com data futura ou com a data 01/01/2000 não comprovam atendimento e são excluídos.
- O prazo inicial de 30 dias é ajustável. A classificação é **possível abandono**, calculada pelo painel; não altera o cadastro nem confirma o motivo da falta de retorno.
- Os códigos de status não filtram o histórico, pois seu significado ainda não foi confirmado.''')
    dates = pd.to_datetime(raw['data'])
    st.write({'Registros sem data':int(dates.isna().sum()),'Registros em 01/01/2000':int(dates.eq(pd.Timestamp('2000-01-01')).sum()),
        'Registros futuros':int(dates.gt(pd.Timestamp(today)).sum())})
