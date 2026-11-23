"""PDF do painel com HTML/CSS e os mesmos objetos Plotly exibidos na tela."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo
import base64
import json
import pandas as pd
from plotly.offline import get_plotlyjs
from playwright.sync_api import sync_playwright


def build_pdf(activity, cohort, display, period, criterion, include_triage, days,
              only_old, search, by_gira=None, charts=None):
    # Streamlit pode executar callbacks em uma thread com event loop ativo.
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_render, activity, cohort, display, period, criterion,
                           include_triage, days, only_old, search, charts or {}).result()


def _render(activity, cohort, display, period, criterion, include_triage, days,
            only_old, search, charts):
    def e(value):
        return escape(str(value))

    def metrics(labels, values):
        return '<div class="metrics">' + ''.join(
            f'<div class="metric"><label>{e(label)}</label><b>{e(value)}</b></div>'
            for label, value in zip(labels, values)) + '</div>'

    jobs = []
    def chart(key, height):
        if key not in charts:
            return '<p>Sem dados no período.</p>'
        spec = json.loads(charts[key].to_json())
        spec['layout'].pop('width', None)
        spec['layout']['height'] = height
        spec['layout']['autosize'] = True
        if key != 'distribuicao':
            spec['layout']['margin'] = dict(l=65, r=20, t=45, b=95 if key == 'triagem' else 65)
            for axis in ['xaxis', 'yaxis']:
                spec['layout'].setdefault(axis, {})['automargin'] = True
        jobs.append((key, spec))
        return f'<div id="{key}" style="height:{height}px"></div>'

    logo = base64.b64encode((Path(__file__).parent/'assets/Novologo.jpg').read_bytes()).decode()
    total = len(cohort)
    single = int(cohort['unico'].sum())
    abandoned = int(cohort['possivel_abandono'].sum())
    eligible = int(cohort['dias_desde_inicio'].ge(days).sum())
    continued, recent = total-single, single-abandoned
    ratio = f'{abandoned/eligible:.1%}'.replace('.', ',') if eligible else '—'
    avg = f"{activity['media']:.1f}".replace('.', ',') if activity['media'] is not None else '—'
    date_label = f'{period[0]:%d/%m/%Y} a {period[1]:%d/%m/%Y}'
    generated = datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')
    css = '''
    @page {size:A4 landscape;margin:10mm 9mm 12mm}
    *{box-sizing:border-box}body{margin:0;background:#eee7f2;color:#202846;font:12px Arial,sans-serif;-webkit-print-color-adjust:exact;print-color-adjust:exact}
    .brand{background:#b695c2;display:flex;align-items:center;gap:22px;padding:12px 22px}.brand img{width:240px}.brand strong{font-size:17px;color:#635079}.brand small{display:block;margin-top:5px}
    .nav{background:white;padding:12px 22px;color:#635079}.hero{background:#202846;color:white;padding:16px 22px}.hero small{color:#c9daf8}.hero h1{font-size:25px;margin:7px 0}.hero p{margin:0;color:#d9e3f6}
    .panel{background:white;border:1px solid #dbe1ea;border-radius:9px;padding:14px;margin:12px 0;break-inside:avoid}.title{font-size:12px;font-weight:bold;border-bottom:1px solid #e5e9ee;padding-bottom:10px;margin-bottom:12px}.title span{float:right;font-weight:normal;color:#655973}
    .metrics{display:flex;gap:12px;margin:12px 0}.metric{flex:1;background:white;border:1px solid #d7e0ef;border-top:3px solid #9470a5;border-radius:7px;padding:14px}.metric:nth-child(2){border-top-color:#b695c2}.metric:nth-child(3){border-top-color:#7c759c}.metric:nth-child(4){border-top-color:#514466}.metric label{display:block;font-size:11px;color:#64736e}.metric b{display:block;font-size:27px;margin-top:8px}
    p,.caption{font-size:11px;line-height:1.5;color:#655973}.info{background:#edf3fb;padding:12px;border-radius:7px;line-height:1.5}.page{break-before:page}.columns{display:flex;gap:12px}.columns>.panel{width:calc((100% - 24px)/3)}
    .flow{display:flex;align-items:center;gap:8px;margin:25px 0;font-size:10px}.flow label{width:96px}.track{flex:1;background:#e6ebf3;height:14px;border-radius:5px;overflow:hidden}.fill{height:100%}.flow b{min-width:28px}
    .statuses{display:flex;gap:7px;margin:28px 0}.status{flex:1;border:1px solid;border-radius:8px;text-align:center;padding:16px 3px;font-size:9px}.status b{display:block;font-size:25px;margin:12px 0}
    table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:9px;background:white}thead{display:table-header-group}th{text-align:left;background:#eee5f2}td,th{padding:8px 5px;border-bottom:1px solid #e5e9ee;overflow-wrap:anywhere}tr{break-inside:avoid}tbody tr:nth-child(even){background:#f8f5fa}h2{font-size:18px}.filters{font-size:11px;line-height:1.6;padding:12px;background:#fff;border-radius:8px;margin:12px 0}
    '''
    html = f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><style>{css}</style><body>
    <div class="brand"><img src="data:image/jpeg;base64,{logo}"><div><strong>GESTÃO DAS GIRAS</strong><small>Acolhimento e acompanhamento</small></div></div>
    <div class="nav">Visão geral &nbsp;&nbsp; | &nbsp;&nbsp; ♡ Giras de cura</div>
    <div class="hero"><small>VISÃO EXECUTIVA</small><h1>Dashboard das giras de cura</h1><p>Início do tratamento, continuidade e possíveis abandonos</p></div>
    <div class="panel"><div class="title">ATENDIMENTOS NAS GIRAS DE CURA <span>{date_label}</span></div>
    {metrics(['Giras de cura no período','Participações no período','Consulentes atendidos','Média de consulentes por gira'],[activity['giras'],activity['participacoes'],activity['consulentes'],avg])}
    <p>{activity['participacoes']} participações: cada consulente conta uma vez por data. A média divide as participações pelas {activity['giras']} datas cadastradas, incluindo datas sem atendimento. Consulentes são pessoas únicas; triagens estão incluídas.</p></div>
    <div class="filters"><b>Filtros do painel</b><br>Período: {date_label}<br>Critério: {e(criterion)} • Triagem: {'incluída' if include_triage else 'excluída'} • Prazo: {days} dias.<br>Lista: {'somente possíveis abandonos' if only_old else 'todos com um atendimento'} • Busca: {e(search.strip() or 'sem filtro')}<br>Exportado em {generated} (São Paulo).</div>
    <div class="page"></div><div class="panel"><div class="title">TRIAGEM × RETORNO POR GIRA</div>
    <p>Uma pessoa por data. Triagem tem prioridade. Retorno = procedimento sem triagem nessa data; não comprova atendimento anterior. Filtros de abandono e inclusão de triagem não alteram este gráfico.</p>{chart('triagem',480)}</div>
    <div class="page"></div><h2>Continuidade do tratamento</h2>
    <div class="info">Critério atual: um único {e(criterion.lower())} no histórico, com pelo menos {days} dias desde o início. Retornos até hoje são verificados mesmo fora do período selecionado.</div>
    {metrics(['Pessoas que iniciaram','Com apenas um atendimento','Possível abandono','Possível abandono / elegíveis'],[total,single,abandoned,ratio])}
    <p>A taxa considera {eligible} pessoa(s) que iniciaram há pelo menos {days} dias. Os casos mais recentes ficam fora do denominador.</p>
    <div class="columns"><div class="panel"><div class="title">ACOMPANHAMENTO <span>{total} pessoas</span></div>'''
    for label, value, color in [('Iniciaram',total,'#514466'),('Mais de um',continued,'#9470a5'),('Apenas um',single,'#b695c2'),('Possível abandono',abandoned,'#855269')]:
        html += f'<div class="flow"><label>{label}</label><div class="track"><div class="fill" style="width:{100*value/max(total,1)}%;background:{color}"></div></div><b>{value}</b></div>'
    html += f'</div><div class="panel"><div class="title">CONTINUIDADE DO TRATAMENTO</div>{chart("distribuicao",240)}</div><div class="panel"><div class="title">SITUAÇÃO DO ACOMPANHAMENTO</div><div class="statuses">'
    for label, value, caption, color, bg in [('MAIS DE UM',continued,'No critério','#2462a4','#edf3fb'),('RECENTES',recent,'Abaixo do prazo','#ac6904','#fff6e7'),('ATENÇÃO',abandoned,'Possível abandono','#b7362e','#fff0ee')]:
        html += f'<div class="status" style="color:{color};background:{bg}">{label}<b>{value}</b>{caption}</div>'
    html += f'''</div><p>Prazo de acompanhamento: {days} dias. A classificação não confirma abandono.</p></div></div>
    <div class="page"></div><div class="panel"><div class="title">EVOLUÇÃO POR MÊS DE INÍCIO</div>{chart('evolucao',350)}</div>
    <div class="filters"><b>Filtros desta exportação</b><br>Período: {date_label} • Critério: {e(criterion)} • Triagem: {'incluída' if include_triage else 'excluída'} • Prazo: {days} dias.<br>Lista: {'somente possíveis abandonos' if only_old else 'todos com um atendimento'} • Busca: {e(search.strip() or 'sem filtro')}.<br>Exportado em {generated} (São Paulo). Dados do estado atual do painel, sem nova consulta.</div>
    <div class="page"></div><h2>Quem possui apenas um atendimento</h2><p>{len(display)} pessoa(s) na lista. Status cadastral exibido sem interpretar os códigos A, D ou F.</p>'''
    if display.empty:
        html += '<div class="panel">Nenhum consulente corresponde aos filtros atuais.</div>'
    else:
        html += '<table><colgroup>' + ''.join(f'<col style="width:{w}%">' for w in [6,24,10,10,8,7,8,8,19]) + '</colgroup><thead><tr>'
        html += ''.join(f'<th>{e(c)}</th>' for c in display.columns) + '</tr></thead><tbody>'
        for row in display.itertuples(index=False, name=None):
            values = [v.strftime('%d/%m/%Y') if isinstance(v,(pd.Timestamp,datetime)) else '' if pd.isna(v) else str(v) for v in row]
            html += '<tr>' + ''.join(f'<td>{e(v)}</td>' for v in values) + '</tr>'
        html += '</tbody></table>'
    html += '</body></html>'
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={'width':1054,'height':740}, device_scale_factor=1)
            page.route('**/*', lambda route: route.abort())
            page.set_content(html, wait_until='load')
            page.add_script_tag(content=get_plotlyjs())
            page.evaluate('''async jobs => {for (const [id, spec] of jobs) {
                await Plotly.newPlot(id,spec.data,spec.layout,{staticPlot:true,displayModeBar:false,responsive:false});
            } await document.fonts.ready;}''', jobs)
            return page.pdf(format='A4', landscape=True, print_background=True,
                display_header_footer=True, header_template='<span></span>',
                footer_template='<div style="font:9px Arial;color:#655973;width:100%;padding:0 35px;display:flex;justify-content:space-between"><span>Casa da Vovó Joaquina | Giras de cura</span><span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span></div>',
                prefer_css_page_size=True)
        finally:
            browser.close()
