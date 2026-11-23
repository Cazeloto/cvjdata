"""Exportação em memória do estado atual do painel, sem novas consultas."""
from io import BytesIO
from pathlib import Path
from html import escape
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart


def build_pdf(activity, cohort, display, period, criterion, include_triage, days, only_old, search, by_gira=None):
    buffer = BytesIO()
    navy, lilac = colors.HexColor('#202846'), colors.HexColor('#b695c2')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SmallCVJ', fontSize=8, leading=11, textColor=navy))
    styles['Title'].textColor = navy
    styles['Heading2'].textColor = navy
    def p(text):
        return Paragraph(escape(str(text)), styles['SmallCVJ'])
    def table(rows, widths, header=True):
        obj = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign='LEFT')
        obj.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'), ('BACKGROUND',(0,0),(-1,0),lilac),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f0f7')]),
            ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
            ('LINEBELOW',(0,0),(-1,0),.5,navy)]))
        return obj
    generated = datetime.now(ZoneInfo('America/Sao_Paulo'))
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=32,leftMargin=32,topMargin=25,bottomMargin=30,
                            title='Dashboard das giras de cura - CVJ',author='Casa da Vovó Joaquina')
    width = landscape(A4)[0]-64
    story = [Image(str(Path(__file__).parent/'assets'/'Novologo.jpg'),width=245,height=92.6,hAlign='LEFT'),
             Paragraph('Dashboard das giras de cura',styles['Title']),
             p(f'Período: {period[0]:%d/%m/%Y} a {period[1]:%d/%m/%Y} | Exportado em {generated:%d/%m/%Y %H:%M} (São Paulo)'),Spacer(1,12)]
    avg = f"{activity['media']:.1f}".replace('.',',') if activity['media'] is not None else '-'
    story += [table([[p(x) for x in ['Giras de cura','Participações no período','Consulentes únicos','Média por gira']],
                     [p(x) for x in [activity['giras'],activity['participacoes'],activity['consulentes'],avg]]],[width/4]*4),Spacer(1,10)]
    eligible = int(cohort['dias_desde_inicio'].ge(days).sum())
    abandoned = int(cohort['possivel_abandono'].sum())
    ratio = f'{abandoned/eligible:.1%}'.replace('.',',') if eligible else '-'
    story += [table([[p(x) for x in ['Pessoas que iniciaram','Com apenas um atendimento','Possível abandono','Taxa entre elegíveis']],
                     [p(x) for x in [len(cohort),int(cohort['unico'].sum()),abandoned,ratio]]],[width/4]*4),Spacer(1,12),
              p(f'Continuidade: {criterion}. Triagem: {"incluída" if include_triage else "excluída"}. Prazo: {days} dias. Elegíveis para a taxa: {eligible}.'),
              p('Atividade: triagens incluídas; cada pessoa conta uma vez por data. A média usa participações / datas de cura cadastradas, incluindo datas sem atendimento registrado.'),
              p('Continuidade: o período filtra o início do tratamento; retornos são verificados em todo o histórico até hoje. Possível abandono é uma indicação para acompanhamento, não uma confirmação.'),
              p(f'Lista: {"somente possíveis abandonos" if only_old else "todos com um atendimento"}. Busca: {search.strip() or "sem filtro"}. Total de linhas: {len(display)}.'),
              p('Fonte: dados carregados no painel (Neon). O PDF preserva o estado exibido e não realiza nova consulta.'),PageBreak(),
              Paragraph('Evolução e continuidade',styles['Heading2'])]
    if not cohort.empty:
        labels = ['Mais de um registro no critério','Único atendimento recente','Possível abandono']
        monthly = cohort.assign(mes=cohort['inicio'].dt.to_period('M')).groupby(['mes','classificacao']).size().unstack(fill_value=0).reindex(columns=labels,fill_value=0)
        # Limita cada gráfico a 18 meses para manter os rótulos legíveis.
        for offset in range(0,len(monthly),18):
            if offset:
                story += [PageBreak(), Paragraph('Evolução mensal - continuação', styles['Heading2'])]
            part = monthly.iloc[offset:offset+18]
            drawing = Drawing(width,240)
            chart = VerticalBarChart()
            chart.x=40;chart.y=40;chart.width=width-60;chart.height=175
            chart.data=[part[col].tolist() for col in labels]
            chart.categoryAxis.categoryNames=[str(x) for x in part.index]
            chart.categoryAxis.labels.fontSize=7
            chart.categoryAxis.style='stacked'
            chart.valueAxis.valueMin=0
            chart.valueAxis.labels.fontSize=8
            for i,color in enumerate(['#514466','#9470a5','#b695c2']):
                chart.bars[i].fillColor=colors.HexColor(color)
                chart.bars[i].strokeColor=None
            drawing.add(chart)
            story += [drawing, p('Legenda: roxo escuro = mais de um registro no critério; roxo médio = único atendimento recente; lilás = possível abandono.'), Spacer(1,12)]
        counts = cohort['classificacao'].value_counts()
        story += [table([[p('Situação'),p('Pessoas')]]+[[p(label),p(int(counts.get(label,0)))] for label in labels],[width*.8,width*.2])]
    else:
        story += [p('Nenhum início de tratamento no período selecionado.')]
    if by_gira is not None and not by_gira.empty:
        for offset in range(0,len(by_gira),14):
            part = by_gira.iloc[offset:offset+14]
            story += [PageBreak(), Paragraph('Triagem x retorno por gira', styles['Heading2']),
                      p('Uma pessoa por data. Triagem tem prioridade. Retorno = procedimento sem triagem na data; não comprova atendimento anterior. Sem descrição é exibido separadamente.')]
            drawing = Drawing(width,270)
            chart = VerticalBarChart()
            chart.x=40;chart.y=60;chart.width=width-60;chart.height=185
            categories = ['Triagem','Retorno'] + (['Sem descrição'] if part['Sem descrição'].sum() else [])
            chart.data=[part[col].tolist() for col in categories]
            chart.categoryAxis.categoryNames=part['data'].dt.strftime('%d/%m/%Y').tolist()
            chart.categoryAxis.labels.fontSize=7
            chart.categoryAxis.labels.angle=30
            chart.valueAxis.valueMin=0
            chart.valueAxis.valueMax=max(1,int(part[categories].to_numpy().max())*1.15)
            for i,color in enumerate(['#b695c2','#514466','#9ca3af'][:len(categories)]):
                chart.bars[i].fillColor=colors.HexColor(color)
                chart.bars[i].strokeColor=None
            drawing.add(chart)
            story += [drawing,p('Legenda: lilás = Triagem; roxo escuro = Retorno; cinza = Sem descrição.'),
                      p(f"Neste gráfico: {part['Triagem'].sum()} triagens e {part['Retorno'].sum()} retornos.")]
    story += [PageBreak(),Paragraph('Lista filtrada de consulentes',styles['Heading2'])]
    if display.empty:
        story += [p('Nenhum consulente corresponde aos filtros atuais.')]
    else:
        headings=['Código','Nome','Primeiro atend.','Último atend.','Dias atend.','Proced.','Dias desde início','Status','Classificação']
        rows=[[p(x) for x in headings]]
        for values in display.itertuples(index=False,name=None):
            rows.append([p(v.strftime('%d/%m/%Y') if isinstance(v,(pd.Timestamp,datetime)) else '' if pd.isna(v) else v) for v in values])
        story.append(table(rows,[width*x for x in [.06,.26,.10,.10,.07,.07,.08,.06,.20]]))
    def footer(canvas, document):
        canvas.setFont('Helvetica',8);canvas.setFillColor(navy)
        canvas.drawString(32,15,'Casa da Vovó Joaquina | Giras de cura')
        canvas.drawRightString(landscape(A4)[0]-32,15,f'Página {document.page}')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buffer.getvalue()
