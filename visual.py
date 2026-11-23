"""Identidade visual compartilhada dos dashboards CVJ."""
from html import escape
from pathlib import Path
import base64
import streamlit as st


def shell(title, subtitle, active='cura'):
    logo = base64.b64encode((Path(__file__).parent / 'assets' / 'Novologo.jpg').read_bytes()).decode('ascii')
    st.markdown('''<style>
    .stApp {background:#eeE7f2;color:#202846}
    [data-testid="stHeader"] {background:#fff}
    .block-container {padding:1rem 1.2rem 2rem;max-width:1600px}
    [data-testid="stSidebar"] {background:#f5f7fa;border-right:1px solid #dbe1ea}
    [data-testid="stSidebar"] * {color:#202846}
    .cvj-brand {background:#b695c2;margin:-1rem -1.2rem 0;padding:16px 24px;display:flex;align-items:center;gap:16px;border-bottom:1px solid #e1e7ee}
    .cvj-logo-img {width:300px;max-width:48%;height:auto;object-fit:contain}
    .cvj-logo {font-size:28px;font-weight:900;font-style:italic;letter-spacing:-2px;color:#244b96;border-right:1px solid #dce3eb;padding-right:20px}
    .cvj-brand strong {color:#635079;font-size:17px;letter-spacing:.6px}
    .cvj-brand small {display:block;color:#38314b;font-size:11px}
    .cvj-brand .right {margin-left:auto;font-size:11px;color:#38314b;letter-spacing:1px}
    .cvj-nav {background:white;display:flex;margin:0 -1.2rem;padding:0 20px;gap:8px}
    .cvj-nav a {text-decoration:none;color:#6c7775;padding:17px 20px;font-size:14px;border-bottom:3px solid transparent}
    .cvj-nav a.active {background:#eee5f2;border-bottom-color:#9470a5;color:#473557}
    .cvj-hero {background:#202846;margin:0 -1.2rem 16px;padding:22px 24px;color:white}
    .cvj-hero small {font-size:11px;font-weight:700;color:#c9daf8;letter-spacing:.8px}
    .cvj-hero h1 {color:white!important;font-size:27px;padding:4px 0 6px;line-height:1.2}
    .cvj-hero p {color:#d9e3f6;font-size:12px;margin:0}
    [data-testid="stMetric"] {background:#fff;border:1px solid #d7e0ef;border-top:3px solid #9470a5;border-radius:7px;padding:16px;min-height:112px}
    [data-testid="stMetricLabel"] {color:#64736e;font-size:12px}
    [data-testid="stMetricValue"] {color:#202846;font-size:28px;font-weight:650}
    [data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"] {border-top-color:#b695c2}
    [data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] {border-top-color:#7c759c}
    [data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] {border-top-color:#514466}
    [data-testid="stVerticalBlockBorderWrapper"]>div, [data-testid="stVerticalBlock"][data-test-scroll-behavior] {background:white;border-radius:10px}
    [data-testid="stExpander"], [data-testid="stAlert"], [data-testid="stDataFrame"] {background:white;border-radius:9px}
    [data-testid="stPlotlyChart"] {background:white;border-radius:9px;padding:6px}
    h2,h3 {color:#202846!important;font-size:17px!important}
    [data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlock"]>[data-testid="stElementContainer"] [data-testid="stCaptionContainer"] {color:#655973}
    [data-testid="stTabs"] {background:#fff;padding:16px;border-radius:10px}
    button[data-baseweb="tab"] {color:#24416e}
    .stButton button,.stDownloadButton button {background:#635079;color:white;border:0;border-radius:7px}
    .panel-title {font-size:12px;font-weight:650;letter-spacing:.2px;color:#202846;border-bottom:1px solid #e5e9ee;padding-bottom:12px;margin-bottom:16px}
    .panel-title span {float:right;color:#89938f;font-weight:400}
    .st-key-follow,.st-key-distribution,.st-key-situation,.st-key-evolution,.st-key-details {background:white;border-radius:10px}
    .st-key-follow,.st-key-distribution,.st-key-situation {min-height:340px}
    .status-grid {display:flex;gap:8px;margin-top:24px}
    .status-box {flex:1;border:1px solid;border-radius:8px;text-align:center;padding:18px 4px}
    .status-box b {display:block;font-size:26px;margin:8px 0}
    .status-box small {font-size:11px}
    .flow-row {display:flex;align-items:center;gap:10px;margin:22px 0;font-size:12px}
    .flow-label {width:115px;color:#606d72}
    .flow-track {height:16px;flex:1;background:#e6ebf3;border-radius:5px;overflow:hidden}
    .flow-fill {height:100%;border-radius:5px;background:#9470a5}
    .flow-row b {min-width:36px;font-size:12px;color:#234884}
    @media(max-width:700px){.cvj-brand .right{display:none}.cvj-nav a{padding:14px 10px}.status-grid{flex-wrap:wrap}}
    </style>''', unsafe_allow_html=True)
    st.markdown(f'''<div class="cvj-brand"><img class="cvj-logo-img" src="data:image/jpeg;base64,{logo}" alt="Casa da Vovó Joaquina"><div><strong>GESTÃO DAS GIRAS</strong><small>Acolhimento e acompanhamento</small></div><div class="right">INDICADORES • CVJ</div></div>
    <nav class="cvj-nav"><a href="/" target="_self" class="{'active' if active=='geral' else ''}">▦ &nbsp; Visão geral</a><a href="/Cura" target="_self" class="{'active' if active=='cura' else ''}">♡ &nbsp; Giras de cura</a><a href="/Fechamento" target="_self" class="{'active' if active=='fechamento' else ''}">Fechamento e cruzamento</a></nav>
    <div class="cvj-hero"><small>VISÃO EXECUTIVA</small><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>''', unsafe_allow_html=True)


def panel_title(title, note=''):
    st.markdown(f'<div class="panel-title">{escape(title)}<span>{escape(note)}</span></div>',unsafe_allow_html=True)


def style_chart(fig, height=300):
    fig.update_layout(height=height,paper_bgcolor='white',plot_bgcolor='white',
        font=dict(color='#202846',size=11),margin=dict(l=12,r=12,t=15,b=15),legend_title_text='')
    return fig
