import logging
import base64
import uuid
import mimetypes
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote
import time
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import streamlit as st
from PIL import Image
from postgrest import SyncPostgrestClient
from supabase import create_client


BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets" / "logo_ipb.png"

# Usa a sarça original como favicon da aba do navegador.
# O arquivo assets/logo_ipb.png deve permanecer no repositório.
if LOGO_PATH.is_file():
    with Image.open(LOGO_PATH) as arquivo_logo:
        ICONE_ABA = arquivo_logo.copy()
else:
    ICONE_ABA = "🌿"  # Fallback se a imagem não estiver disponível.

st.set_page_config(
    page_title="Sistema de Gestão Patrimonial IPB - CABO",
    page_icon=ICONE_ABA,
    layout="wide",
    initial_sidebar_state="auto",
)
LOG = logging.getLogger("patrimonio_ipb")

st.markdown("""
<style>
:root { color-scheme: dark; }
.stApp, [data-testid="stAppViewContainer"] { background: #073f30 !important; color: #fff !important; }
[data-testid="stHeader"] { background: rgba(7,63,48,.96) !important; }
[data-testid="stSidebar"] { background: #052e23 !important; border-right: 1px solid #28624e; }
[data-testid="stSidebar"] * { color: #fff !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { border-radius: 10px; padding: 6px; }
h1, h2, h3, h4, p, label, [data-testid="stCaptionContainer"] { color: #fff !important; }
[data-testid="stMetric"] { background: #fff; border: 1px solid #d6e7dc; border-radius: 15px; padding: 18px; }
[data-testid="stMetric"] * { color: #073f30 !important; }
[data-testid="stForm"] { background: #fff; border: 1px solid #d9e8dd; border-radius: 16px; padding: 22px; box-shadow: 0 12px 30px #001e141a; }
[data-testid="stForm"] p, [data-testid="stForm"] label, [data-testid="stForm"] [data-testid="stWidgetLabel"] * { color: #103f30 !important; }
[data-testid="stForm"] [data-testid="stCaptionContainer"] * { color: #476757 !important; }
[data-testid="stForm"] input, [data-testid="stForm"] textarea { color: #153b2f !important; }
[data-testid="stForm"] [data-baseweb="select"] * { color: #153b2f !important; }
[data-testid="stFormSubmitButton"] button, .stButton button[kind="primary"] { background: #006341 !important; border: 1px solid #006341 !important; color: white !important; border-radius: 10px !important; font-weight: 700 !important; }
[data-testid="stFormSubmitButton"] button *, .stButton button[kind="primary"] * { color: white !important; }
[data-testid="stFormSubmitButton"] button:hover, .stButton button[kind="primary"]:hover { background: #004b32 !important; border-color: #004b32 !important; }
[data-testid="stSidebar"] .stButton button { border-color: #8ebba8 !important; }
[data-testid="stSidebar"] .stButton button:hover { background: #176247 !important; }
[data-testid="stAlert"] p { color: inherit !important; }
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
hr { border-color: #37715d !important; }
.ipb-banner { background: #10543d; border: 1px solid #337b60; border-radius: 16px; padding: 20px 24px; margin: 10px 0 22px; }
.ipb-banner h1 { font-size: clamp(1.5rem, 3vw, 2.3rem); margin: 0 0 5px; }
.ipb-banner p { margin: 0; color: #cce7d8 !important; }
@media(max-width: 768px) { [data-testid="stForm"] { padding: 12px; } .ipb-banner { padding: 15px; } }

.ipb-banner {display:flex; align-items:center; gap:23px; min-height:150px; background:linear-gradient(110deg,#075239,#10543d 75%,#0a7651); border:1px solid #5ca57f; box-shadow:0 8px 25px rgba(0,0,0,.12);}
.ipb-banner-logo {width:112px; height:112px; object-fit:contain; flex-shrink:0; padding-right:18px; border-right:2px solid #b8dfc8;}
.ipb-banner-copy {min-width:0;}
.ipb-banner-copy h1 {line-height:1.18;}
@media(max-width:768px) {.ipb-banner{gap:12px;min-height:100px}.ipb-banner-logo{width:72px;height:72px;padding-right:10px}.ipb-banner-copy h1{font-size:1.24rem}}
/* O controle recolhido é um botão do cabeçalho, não o menu de três pontos. */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"] {z-index:1000 !important;}
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"] button,
button[data-testid="stBaseButton-headerNoPadding"]:has(svg[data-testid="stIconMaterial"]),
[data-testid="stSidebarHeader"] button {
  background:#08744f !important; border:2px solid #b0e6c6 !important;
  color:#fff !important; border-radius:12px !important;
  min-width:46px !important; min-height:46px !important;
  box-shadow:0 3px 12px #001f1670 !important;
}
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarHeader"] button svg {stroke:white !important; width:25px !important; height:25px !important;}


/* Navegação lateral IPB: mantém a estrutura e a sarça original */
[data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] {
    gap: 7px !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    display: flex !important;
    align-items: center !important;
    min-height: 43px !important;
    padding: 10px 13px !important;
    border: 1px solid transparent !important;
    border-radius: 12px !important;
    background: rgba(255,255,255,.035) !important;
    transition: background .18s, border-color .18s, transform .18s;
    cursor: pointer !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: #135a43 !important;
    border-color: #41866a !important;
    transform: translateX(2px);
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: #176b4c !important;
    border-color: #62b58a !important;
    box-shadow: inset 3px 0 0 #b7e9c6 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label [data-testid="stMarkdownContainer"] p {
    font-size: .93rem !important;
    font-weight: 550 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) [data-testid="stMarkdownContainer"] p {
    font-weight: 750 !important;
}
/* Esconde apenas o marcador circular, sem desativar a seleção acessível */
[data-testid="stSidebar"] [data-testid="stRadio"] label [data-baseweb="radio"] > div:first-child {
    display: none !important;
}
/* Botão nativo do Streamlit para abrir/recolher a barra lateral */
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarHeader"] button,
[data-testid="stHeader"] button[kind="header"] {
    min-width: 43px !important;
    min-height: 43px !important;
    border: 1px solid #9bd5b1 !important;
    border-radius: 12px !important;
    background: #176b4c !important;
    color: white !important;
    box-shadow: 0 3px 12px rgba(0,0,0,.24) !important;
}
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="stSidebarHeader"] button:hover,
[data-testid="stHeader"] button[kind="header"]:hover {
    background: #239060 !important;
    border-color: #e1ffe9 !important;
}
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="stSidebarHeader"] button svg,
[data-testid="stHeader"] button[kind="header"] svg {
    width: 23px !important;
    height: 23px !important;
    stroke: #fff !important;
}
@media(max-width:768px) {
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stSidebarHeader"] button { min-width: 46px !important; min-height: 46px !important; }
}

.ipb-banner .ipb-igreja-nome { font-size: clamp(1.5rem, 3vw, 2.3rem) !important; font-weight: 750 !important; color: #ffffff !important; margin: 0 0 8px !important; line-height:1.18; }

/* Cabeçalho institucional: nome da igreja em destaque, sistema logo abaixo. */
.ipb-banner-copy { display:flex; flex-direction:column; justify-content:center; gap:3px; }
.ipb-banner .ipb-igreja-nome {
    font-size:clamp(1.35rem, 2.5vw, 2.15rem) !important;
    font-weight:800 !important; color:#fff !important;
    line-height:1.16 !important; margin:0 !important;
}
.ipb-banner .ipb-sistema-nome {
    font-size:clamp(1.05rem, 1.7vw, 1.5rem) !important;
    font-weight:600 !important; color:#e0f2e7 !important;
    line-height:1.2 !important; margin:0 !important;
}
@media(max-width:768px) {
    .ipb-banner-copy { gap:4px; }
    .ipb-banner .ipb-igreja-nome { font-size:1.3rem !important; }
    .ipb-banner .ipb-sistema-nome { font-size:1.05rem !important; }
}

/* IPB CABO — aperfeiçoamentos responsivos sem alterar a lógica dos módulos. */
html { -webkit-text-size-adjust: 100%; }
.stApp { overflow-x: clip; }
[data-testid="stAppViewBlockContainer"] { max-width: 1320px; }
[data-testid="stWidgetLabel"] p { line-height: 1.35; }
[data-testid="stForm"] { min-width: 0; }
[data-testid="stForm"] button,
[data-testid="stFileUploader"] button,
[data-testid="stDownloadButton"] button {
    border-radius: 11px !important;
}
[data-testid="stDataFrame"], [data-testid="stTable"] {
    max-width: 100%; overflow-x: auto;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    min-height: 48px !important;
}
@media (max-width: 768px) {
    /* Mais área útil e elementos tocáveis em telefones. */
    [data-testid="stAppViewBlockContainer"] {
        padding: 1.1rem .78rem 3rem !important;
        max-width: 100% !important;
    }
    [data-testid="stMainBlockContainer"] { max-width: 100% !important; }
    [data-testid="stHeader"] { height: 3.3rem; }
    [data-testid="stSidebar"] { max-width: min(88vw, 330px) !important; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        min-height: 50px !important;
        padding: 12px 13px !important;
    }
    .ipb-banner {
        display: flex !important;
        align-items: center !important;
        gap: 11px !important;
        min-height: unset !important;
        padding: 14px 12px !important;
        margin: 6px 0 16px !important;
        border-radius: 13px !important;
    }
    .ipb-banner-logo {
        width: 55px !important;
        height: 63px !important;
        padding-right: 9px !important;
        flex: 0 0 55px !important;
    }
    .ipb-banner-copy { min-width: 0 !important; gap: 5px !important; }
    .ipb-banner .ipb-igreja-nome {
        font-size: clamp(.96rem, 3.8vw, 1.22rem) !important;
        line-height: 1.19 !important;
        overflow-wrap: anywhere;
    }
    .ipb-banner .ipb-sistema-nome {
        font-size: clamp(.77rem, 3vw, .96rem) !important;
        line-height: 1.2 !important;
        overflow-wrap: anywhere;
    }
    [data-testid="stForm"] {
        padding: 13px 11px !important;
        border-radius: 13px !important;
    }
    [data-testid="stForm"] [data-testid="stHorizontalBlock"] {
        gap: .55rem !important;
    }
    [data-testid="stFormSubmitButton"] button,
    [data-testid="stDownloadButton"] button,
    [data-testid="stFileUploader"] button {
        min-height: 46px !important;
        max-width: 100%;
    }
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-baseweb="select"] input {
        font-size: 16px !important; /* evita zoom involuntário no iPhone */
        min-height: 43px;
    }
    [data-testid="stRadio"] [role="radiogroup"] {
        flex-wrap: wrap !important;
        row-gap: .45rem !important;
    }
    [data-testid="stRadio"] [role="radiogroup"] label {
        min-height: 42px;
    }
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        overflow-x: auto !important;
        flex-wrap: nowrap !important;
        scrollbar-width: thin;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        flex-shrink: 0;
        min-height: 45px;
    }
    .ipb-dashboard-intro {
        padding: 14px !important;
        border-radius: 13px !important;
    }
    .ipb-kpi {
        min-height: 100px !important;
        padding: 14px 13px !important;
        border-radius: 13px !important;
    }
    .ipb-kpi .ipb-kpi-value { font-size: 1.85rem !important; margin-top: 6px !important; }
    .ipb-kpi .ipb-kpi-label { font-size: .8rem !important; }
    [data-testid="stMetric"] { padding: 12px !important; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    [data-testid="stDataFrame"] { min-width: 0; }
    .stImage img { max-width: 100%; height: auto; }
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }
}
@media (max-width: 380px) {
    .ipb-banner-logo { width: 43px !important; flex-basis: 43px !important; }
    .ipb-banner .ipb-igreja-nome { font-size: .92rem !important; }
    .ipb-banner .ipb-sistema-nome { font-size: .76rem !important; }
}


/* CONTRASTE IPB: ícones de abrir/fechar menu, inclusive variantes Material. */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarHeader"] { z-index: 1001 !important; }
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarHeader"] button,
[data-testid="stSidebar"] button[aria-label*="Close sidebar"],
[data-testid="stHeader"] button[aria-label*="Open sidebar"] {
  display: inline-flex !important; align-items: center !important; justify-content: center !important;
  background: #15865e !important; color: #fff !important;
  border: 2px solid #e0ffec !important; border-radius: 12px !important;
  min-width: 48px !important; min-height: 48px !important;
  opacity: 1 !important; box-shadow: 0 2px 13px rgba(0,0,0,.42) !important;
}
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebarHeader"] button:hover { background: #20a572 !important; }
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarHeader"] button svg,
[data-testid="stSidebarCollapsedControl"] button svg *,
[data-testid="stSidebarCollapseButton"] button svg *,
[data-testid="stSidebarHeader"] button svg * {
  color: #fff !important; stroke: #fff !important; fill: none !important;
  opacity: 1 !important; width: 27px !important; height: 27px !important;
}
[data-testid="stSidebarCollapsedControl"] button [data-testid="stIconMaterial"],
[data-testid="stSidebarCollapseButton"] button [data-testid="stIconMaterial"],
[data-testid="stSidebarHeader"] button [data-testid="stIconMaterial"],
[data-testid="stSidebarCollapsedControl"] button span,
[data-testid="stSidebarCollapseButton"] button span,
[data-testid="stSidebarHeader"] button span {
  color: #fff !important; opacity: 1 !important; font-size: 27px !important;
}
/* Letras claras em superfícies escuras; sem tornar texto branco sobre fundo branco. */
[data-testid="stAppViewContainer"], [data-testid="stSidebar"],
[data-testid="stAppViewContainer"] h1, [data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3, [data-testid="stAppViewContainer"] h4,
[data-testid="stAppViewContainer"] p, [data-testid="stSidebar"] p,
[data-testid="stWidgetLabel"] *, [data-testid="stMarkdownContainer"] {
  color: #fff !important;
}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div {
  background-color: #164d3d !important; color: #fff !important;
  border-color: #75ac94 !important;
}
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input, [data-testid="stTextArea"] textarea,
[data-baseweb="select"] input, [data-baseweb="select"] span,
[data-baseweb="select"] svg, [data-baseweb="input"] input {
  color: #fff !important; fill: #fff !important;
}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder { color: #d2e6dc !important; }
[data-testid="stForm"] [data-baseweb="select"] * { color: #fff !important; }
/* Tabelas HTML e campos editáveis permanecem legíveis em fundo verde. */
[data-testid="stTable"] table, [data-testid="stTable"] th,
[data-testid="stTable"] td { background: #164d3d !important; color: #fff !important; }
[data-testid="stDataFrame"] { color: #fff !important; }


/* BOTÕES DE MENU — texto MENU em vez de setas, preservando o clique nativo. */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarHeader"]:has(button[aria-label*="sidebar"]),
[data-testid="stHeader"]:has(button[aria-label*="sidebar"]) {
  overflow: visible !important;
  z-index: 99999 !important;
}
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarHeader"] button[aria-label*="sidebar"],
[data-testid="stHeader"] button[aria-label*="sidebar"] {
  position: relative !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 78px !important;
  height: 54px !important;
  min-width: 78px !important;
  min-height: 54px !important;
  background-color: #24a36e !important;
  border: 3px solid #ffffff !important;
  border-radius: 13px !important;
  opacity: 1 !important;
  visibility: visible !important;
  box-shadow: 0 0 0 2px #063c2c, 0 3px 12px #0008 !important;
  cursor: pointer !important;
}
/* O texto branco permanece visível mesmo se o Streamlit trocar SVG por Material Icons. */
[data-testid="stSidebarCollapsedControl"] button::after,
[data-testid="stSidebarCollapseButton"] button::after,
[data-testid="stSidebarHeader"] button[aria-label*="sidebar"]::after,
[data-testid="stHeader"] button[aria-label*="sidebar"]::after {
  content: "MENU" !important;
  position: absolute !important;
  inset: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  color: #ffffff !important;
  font: 800 12px/1 Arial, sans-serif !important; letter-spacing: .25px !important;
  text-shadow: 0 1px 2px #003e2c !important;
  pointer-events: none !important;
  opacity: 1 !important;
}
[data-testid="stSidebarCollapsedControl"] button::after,
[data-testid="stHeader"] button[aria-label*="Open sidebar"]::after,
[data-testid="stHeader"] button[aria-label*="open sidebar"]::after {
  content: "MENU" !important;
}
/* Menu aberto: seta para a esquerda dentro do botão, ao lado do texto menor. */
[data-testid="stSidebarCollapseButton"] button::after,
[data-testid="stSidebarHeader"] button[aria-label*="sidebar"]::after {
  content: "❮  MENU" !important;
}
[data-testid="stSidebarHeader"] button[aria-label*="Close"]::after,
[data-testid="stSidebarHeader"] button[aria-label*="close"]::after {
  content: "❮  MENU" !important;
}
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarHeader"] button[aria-label*="sidebar"] svg,
[data-testid="stHeader"] button[aria-label*="sidebar"] svg,
[data-testid="stSidebarCollapsedControl"] button [data-testid="stIconMaterial"],
[data-testid="stSidebarCollapseButton"] button [data-testid="stIconMaterial"] {
  opacity: 0 !important;
}
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebarHeader"] button[aria-label*="sidebar"]:hover,
[data-testid="stHeader"] button[aria-label*="sidebar"]:hover {
  background: #36bd84 !important;
}
@media(max-width:768px) {
  [data-testid="stSidebarCollapsedControl"] button,
  [data-testid="stSidebarCollapseButton"] button,
  [data-testid="stSidebarHeader"] button[aria-label*="sidebar"],
  [data-testid="stHeader"] button[aria-label*="sidebar"] {
    width: 76px !important; height: 52px !important;
    min-width: 76px !important; min-height: 52px !important;
  }
}


/* MENU ABERTO: apenas seta branca, sem quadrado, fundo ou borda. */
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarHeader"] button[aria-label*="sidebar"],
[data-testid="stSidebarHeader"] button[aria-label*="Close"],
[data-testid="stSidebarHeader"] button[aria-label*="close"] {
  width: 42px !important;
  min-width: 42px !important;
  height: 44px !important;
  min-height: 44px !important;
  background: transparent !important;
  background-color: transparent !important;
  border: 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  outline: none !important;
  padding: 0 !important;
}
[data-testid="stSidebarCollapseButton"] button::after,
[data-testid="stSidebarHeader"] button[aria-label*="sidebar"]::after,
[data-testid="stSidebarHeader"] button[aria-label*="Close"]::after,
[data-testid="stSidebarHeader"] button[aria-label*="close"]::after {
  content: "❮" !important;
  color: #fff !important;
  font: 900 29px/1 Arial, sans-serif !important;
  text-shadow: 0 1px 3px #002b1d !important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebarHeader"] button[aria-label*="sidebar"]:hover,
[data-testid="stSidebarHeader"] button[aria-label*="Close"]:hover,
[data-testid="stSidebarHeader"] button[aria-label*="close"]:hover {
  background: transparent !important;
  box-shadow: none !important;
}
@media (max-width:768px) {
  [data-testid="stSidebarCollapseButton"] button,
  [data-testid="stSidebarHeader"] button[aria-label*="sidebar"] {
    width: 42px !important; min-width: 42px !important;
    height: 44px !important; min-height: 44px !important;
  }
}


/* Menu principal horizontal: estilo profissional e responsivo */
.st-key-navegacao_ipb [data-testid="stRadio"] > div[role="radiogroup"],
[data-testid="stRadio"].st-key-navegacao_ipb > div[role="radiogroup"] {
  display:flex !important; flex-wrap:nowrap !important; gap:0 !important;
  overflow-x:auto !important; padding:5px !important;
  background:linear-gradient(115deg,#064333,#022d23) !important;
  border:1px solid #398267 !important; border-radius:17px !important;
  box-shadow:0 8px 22px #001e1659 !important;
  scrollbar-width:thin;
}
.st-key-navegacao_ipb [data-testid="stRadio"] label,
[data-testid="stRadio"].st-key-navegacao_ipb label {
  flex:1 0 auto !important; min-height:62px !important;
  padding:12px 15px !important; border-radius:12px !important;
  display:flex !important; align-items:center !important; justify-content:center !important;
  background:transparent !important; border:1px solid transparent !important;
  cursor:pointer !important; transition:background .15s ease !important;
}
.st-key-navegacao_ipb [data-testid="stRadio"] label:hover,
[data-testid="stRadio"].st-key-navegacao_ipb label:hover {background:#14674d !important;}
.st-key-navegacao_ipb [data-testid="stRadio"] label:has(input:checked),
[data-testid="stRadio"].st-key-navegacao_ipb label:has(input:checked) {
  background:linear-gradient(180deg,#08a66c,#087b50) !important;
  border-color:#3ad49b !important; box-shadow:inset 0 -3px 0 #c7ffdf !important;
}
.st-key-navegacao_ipb [data-testid="stRadio"] label p,
[data-testid="stRadio"].st-key-navegacao_ipb label p {
  color:white !important; font-size:.88rem !important; font-weight:700 !important;
  white-space:nowrap !important;
}
.st-key-navegacao_ipb [data-testid="stRadio"] label [data-baseweb="radio"] > div:first-child,
[data-testid="stRadio"].st-key-navegacao_ipb label [data-baseweb="radio"] > div:first-child {display:none !important;}
@media(max-width:768px){
 .st-key-navegacao_ipb [data-testid="stRadio"] label,
 [data-testid="stRadio"].st-key-navegacao_ipb label {min-height:48px !important; padding:9px 12px !important;}
}

/* CORREÇÃO DE LEGIBILIDADE — caixas de seleção, abertas ou sem hover. */
[data-baseweb="select"] > div,
[data-baseweb="select"] > div:hover,
[data-baseweb="select"] > div:focus-within {
  background-color: #164d3d !important;
  border-color: #83c6a8 !important;
  color: #ffffff !important;
}
[data-baseweb="select"] input,
[data-baseweb="select"] [data-testid="stMarkdownContainer"],
[data-baseweb="select"] span {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}
/* Listas suspensas do BaseWeb são renderizadas fora dos formulários. */
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="popover"] ul,
[data-baseweb="menu"] {
  background-color: #103f30 !important;
  color: #ffffff !important;
}
[data-baseweb="popover"] [role="option"],
[data-baseweb="popover"] li,
[data-baseweb="menu"] [role="option"] {
  background-color: #103f30 !important;
  color: #ffffff !important;
}
[data-baseweb="popover"] [role="option"] *,
[data-baseweb="popover"] li *,
[data-baseweb="menu"] [role="option"] * {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [role="option"][aria-selected="true"],
[data-baseweb="popover"] li:hover,
[data-baseweb="menu"] [role="option"]:hover {
  background-color: #187855 !important;
  color: #ffffff !important;
}
/* Campos desabilitados mantêm contraste. */
[data-baseweb="select"] [aria-disabled="true"] {opacity:.75 !important;}
</style>
""", unsafe_allow_html=True)


def mostrar_logo(largura=120):
    if LOGO_PATH.is_file():
        try:
            with Image.open(LOGO_PATH) as imagem:
                st.image(imagem.copy(), width=largura)
        except Exception:
            st.caption("IPB - CABO")
    else:
        st.caption("IPB - CABO")


def cliente_auth():
    return create_client(st.secrets["SUPABASE_URL"].rstrip("/"), st.secrets["SUPABASE_ANON_KEY"])


def api_usuario(token):
    return SyncPostgrestClient(
        st.secrets["SUPABASE_URL"].rstrip("/") + "/rest/v1",
        headers={
            "apikey": st.secrets["SUPABASE_ANON_KEY"],
            "Authorization": "Bearer " + token,
        },
    )


def consultar_perfil(token, user_id):
    resposta = (
        api_usuario(token).from_("perfis")
        .select("id,nome_completo,papel,ativo")
        .eq("id", user_id).limit(1).execute()
    )
    return resposta.data[0] if resposta.data else None


def limpar_sessao():
    for chave in ("access_token", "refresh_token", "user_id", "profile", "expires_at"):
        st.session_state.pop(chave, None)


def autenticar(email, senha):
    resposta = cliente_auth().auth.sign_in_with_password({"email": email, "password": senha})
    if not resposta.session or not resposta.user:
        raise ValueError("O Supabase não retornou uma sessão válida.")
    perfil = consultar_perfil(resposta.session.access_token, resposta.user.id)
    if not perfil or not perfil.get("ativo"):
        raise PermissionError("Usuário autenticado, mas sem perfil ativo/autorizado na tabela perfis.")
    st.session_state.update({
        "access_token": resposta.session.access_token,
        "refresh_token": resposta.session.refresh_token,
        "user_id": resposta.user.id,
        "profile": perfil,
        "expires_at": resposta.session.expires_at or (int(time.time()) + resposta.session.expires_in),
    })


def validar_sessao():
    if not st.session_state.get("refresh_token"):
        return False
    if st.session_state.get("access_token") and int(st.session_state.get("expires_at") or 0) > time.time() + 90 and st.session_state.get("profile", {}).get("ativo"):
        return True
    try:
        resposta = cliente_auth().auth.refresh_session(st.session_state["refresh_token"])
        if not resposta.session or not resposta.user:
            return False
        if resposta.user.id != st.session_state.get("user_id"):
            return False
        perfil = consultar_perfil(resposta.session.access_token, resposta.user.id)
        if not perfil or not perfil.get("ativo"):
            return False
        st.session_state.update({
            "access_token": resposta.session.access_token,
            "refresh_token": resposta.session.refresh_token,
            "profile": perfil,
            "expires_at": resposta.session.expires_at or (int(time.time()) + resposta.session.expires_in),
        })
        return True
    except Exception:
        LOG.exception("Falha ao validar a sessão")
        return False


def explicar_erro_login(erro):
    nome = type(erro).__name__
    mensagem = str(erro).lower()
    if isinstance(erro, PermissionError):
        return str(erro)
    if "invalid login credentials" in mensagem or "invalid credentials" in mensagem:
        return "E-mail ou senha inválidos. Confira os dados e tente novamente."
    if "email not confirmed" in mensagem:
        return "O e-mail ainda não foi confirmado no Supabase Auth."
    if "getaddrinfo" in mensagem or "connecterror" in nome.lower():
        return "Não foi possível localizar o servidor Supabase. Confira SUPABASE_URL em Secrets."
    if "permission denied" in mensagem or "row-level security" in mensagem:
        return "O Supabase bloqueou a consulta do perfil. Verifique as políticas RLS."
    if isinstance(erro, KeyError):
        return "Configuração ausente em Secrets: confira SUPABASE_URL e SUPABASE_ANON_KEY."
    return f"Falha no login ({nome}). Consulte os logs do Streamlit; não compartilhe chaves nem tokens."


def tela_login():
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    _, centro, _ = st.columns([1, 1.5, 1])
    with centro:
        _, logo_col, _ = st.columns([1, 1, 1])
        with logo_col:
            mostrar_logo(130)
        st.markdown("""
        <h1 style="text-align:center;font-size:clamp(1.7rem,3vw,2.2rem);margin:8px 0;">Sistema de Gestão Patrimonial</h1>
        <p style="text-align:center;font-weight:750;letter-spacing:3px;color:#c9ebd9 !important;">IPB - CABO</p>
        <p style="text-align:center;color:#b9d7c8 !important;">Acesso restrito a usuários autorizados</p>
        """, unsafe_allow_html=True)
        with st.form("login"):
            email = st.text_input("E-mail", placeholder="Digite seu e-mail")
            senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            enviar = st.form_submit_button("Entrar no sistema", type="primary", use_container_width=True)
        if enviar:
            if not email.strip() or not senha:
                st.warning("Informe o e-mail e a senha.")
            else:
                try:
                    autenticar(email.strip(), senha)
                    st.rerun()
                except Exception as erro:
                    # Não registrar a exceção completa do provedor de autenticação:
                    # algumas bibliotecas podem incluir dados sensíveis na mensagem.
                    LOG.warning("Login falhou: %s", type(erro).__name__)
                    st.error(explicar_erro_login(erro))
    st.stop()


def listar_referencias(tabela):
    resposta = (
        api_usuario(st.session_state["access_token"])
        .from_(tabela).select("id,nome,ativo")
        .eq("ativo", True).order("nome").execute()
    )
    return resposta.data or []


def listar_patrimonios():
    # A paginação evita o limite padrão de 1.000 registros do PostgREST.
    itens = []
    pagina = 0
    tamanho = 500
    while True:
        resposta = (
            api_usuario(st.session_state["access_token"])
            .from_("patrimonios")
            .select("id,codigo,descricao,categoria_id,localizacao_id,marca,modelo,numero_serie,data_aquisicao,valor_aquisicao,estado_conservacao,situacao,subgrupo,observacoes,foto_caminho,nota_fiscal_caminho,criado_em,atualizado_em")
            .order("codigo")
            .range(pagina * tamanho, (pagina + 1) * tamanho - 1)
            .execute()
        )
        lote = resposta.data or []
        itens.extend(lote)
        if len(lote) < tamanho:
            break
        pagina += 1
    return itens


def opcoes_referencia(itens):
    return {item["id"]: item["nome"] for item in itens}


def id_opcional(valor):
    return valor if valor else None


def data_opcional(valor):
    return valor.isoformat() if valor else None


def decimal_opcional(valor_texto):
    texto = valor_texto.strip()
    if not texto:
        return None
    texto = texto.replace(".", "").replace(",", ".") if "," in texto else texto
    try:
        numero = Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError("Valor de aquisição inválido. Exemplo: 1500,00") from exc
    if not numero.is_finite() or numero < 0:
        raise ValueError("O valor de aquisição deve ser um número positivo ou zero.")
    return float(numero)


# Fotos dos patrimônios em bucket privado; sem chave service_role.
BUCKET_FOTOS = "ipb-patrimonios"
LIMITE_FOTO = 5 * 1024 * 1024


def requisicao_foto(metodo, caminho, dados=None, mime=None):
    url = (st.secrets["SUPABASE_URL"].rstrip("/") +
           "/storage/v1/object/" + BUCKET_FOTOS + "/" + quote(caminho, safe="/"))
    headers = {
        "apikey": st.secrets["SUPABASE_ANON_KEY"],
        "Authorization": "Bearer " + st.session_state["access_token"],
    }
    if mime:
        headers["Content-Type"] = mime
    if metodo == "POST":
        headers["x-upsert"] = "false"
    with urlopen(Request(url, data=dados, headers=headers, method=metodo), timeout=45) as resp:
        return resp.read()


def validar_foto(arquivo):
    if arquivo is None:
        return None
    dados = arquivo.getvalue()
    if not dados or len(dados) > LIMITE_FOTO:
        raise ValueError("A foto deve ter até 5 MB.")
    from io import BytesIO
    try:
        with Image.open(BytesIO(dados)) as imagem:
            formato = imagem.format
            imagem.verify()
    except Exception as exc:
        raise ValueError("Imagem inválida. Use JPG, PNG ou WEBP.") from exc
    formatos = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"),
                "WEBP": ("webp", "image/webp")}
    if formato not in formatos:
        raise ValueError("Formato não permitido. Use JPG, PNG ou WEBP.")
    extensao, mime = formatos[formato]
    return dados, extensao, mime


def salvar_foto_patrimonio(patrimonio_id, arquivo):
    validada = validar_foto(arquivo)
    if validada is None:
        return False
    dados, extensao, mime = validada
    caminho = f"{patrimonio_id}/{uuid.uuid4().hex}.{extensao}"
    requisicao_foto("POST", caminho, dados, mime)
    try:
        resposta = (api_usuario(st.session_state["access_token"])
                    .from_("patrimonios").update({"foto_caminho": caminho})
                    .eq("id", patrimonio_id).execute())
        if not resposta.data:
            raise RuntimeError("O banco não confirmou a atualização da foto.")
    except Exception:
        # Tenta retirar o arquivo órfão caso o vínculo falhe.
        try:
            requisicao_foto("DELETE", caminho)
        except Exception:
            pass
        raise
    return True



# Notas fiscais armazenadas em bucket privado independente das fotos.
BUCKET_NOTAS = "ipb-notas-fiscais"
LIMITE_NOTA = 10 * 1024 * 1024


def requisicao_nota(metodo, caminho, dados=None, mime=None):
    url = (st.secrets["SUPABASE_URL"].rstrip("/") +
           "/storage/v1/object/" + BUCKET_NOTAS + "/" + quote(caminho, safe="/"))
    headers = {
        "apikey": st.secrets["SUPABASE_ANON_KEY"],
        "Authorization": "Bearer " + st.session_state["access_token"],
    }
    if mime:
        headers["Content-Type"] = mime
    if metodo == "POST":
        headers["x-upsert"] = "false"
    with urlopen(Request(url, data=dados, headers=headers, method=metodo), timeout=45) as resp:
        return resp.read()


def validar_nota_fiscal(arquivo):
    if arquivo is None:
        return None
    dados = arquivo.getvalue()
    if not dados or len(dados) > LIMITE_NOTA:
        raise ValueError("A nota fiscal deve ter até 10 MB.")
    nome = arquivo.name.lower()
    if nome.endswith(".pdf") and dados.startswith(b"%PDF-"):
        return dados, "pdf", "application/pdf"
    from io import BytesIO
    try:
        with Image.open(BytesIO(dados)) as imagem:
            formato = imagem.format
            imagem.verify()
    except Exception as exc:
        raise ValueError("Nota fiscal inválida. Anexe PDF, JPG ou PNG.") from exc
    tipos = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png")}
    if formato not in tipos:
        raise ValueError("Formato inválido. Anexe PDF, JPG ou PNG.")
    extensao, mime = tipos[formato]
    return dados, extensao, mime


def salvar_nota_fiscal(patrimonio_id, arquivo):
    dados, extensao, mime = validar_nota_fiscal(arquivo)
    caminho = f"{patrimonio_id}/{uuid.uuid4().hex}.{extensao}"
    requisicao_nota("POST", caminho, dados, mime)
    try:
        resposta = (api_usuario(st.session_state["access_token"])
                    .from_("patrimonios").update({"nota_fiscal_caminho": caminho})
                    .eq("id", patrimonio_id).execute())
        if not resposta.data:
            raise RuntimeError("Não foi possível vincular a nota fiscal ao patrimônio.")
    except Exception:
        try:
            requisicao_nota("DELETE", caminho)
        except Exception:
            pass
        raise


def exibir_nota_fiscal(registro):
    caminho = registro.get("nota_fiscal_caminho")
    if not caminho:
        st.caption("Nota fiscal não anexada.")
        return
    try:
        dados = requisicao_nota("GET", caminho)
        extensao = caminho.rsplit(".", 1)[-1].lower()
        mime = {"pdf": "application/pdf", "jpg": "image/jpeg", "png": "image/png"}.get(extensao, "application/octet-stream")
        st.download_button("Baixar nota fiscal", dados,
                           file_name=f"nota_fiscal_{registro.get('codigo') or 'patrimonio'}.{extensao}",
                           mime=mime, key=f"nota_fiscal_download_{registro['id']}")
    except Exception:
        st.warning("Não foi possível acessar a nota fiscal. Confira as permissões do Storage.")

def exibir_foto_patrimonio(registro):
    caminho = registro.get("foto_caminho")
    if not caminho:
        st.info("Este patrimônio ainda não possui foto cadastrada.")
        return
    try:
        dados = requisicao_foto("GET", caminho)
        st.image(dados, caption=f"{registro.get('codigo', '')} — {registro.get('descricao', '')}",
                 use_container_width=False, width=360)
    except Exception:
        st.warning("Não foi possível carregar a foto. Verifique as permissões do Storage.")


def formulario_patrimonio(chave, categorias, localizacoes, registro=None):
    edicao = registro is not None
    categorias_map = opcoes_referencia(categorias)
    locais_map = opcoes_referencia(localizacoes)
    cat_ids = [""] + list(categorias_map)
    loc_ids = [""] + list(locais_map)
    subgrupos = ["Não informado", "SOM", "MÍDIA", "CONSELHO", "SAF", "MINISTÉRIO INFANTIL", "UME", "UPA", "UPH", "GRUPO DE MÚSICA"]
    estados = ["", "Novo", "Bom", "Regular", "Ruim"]
    estado_atual = (registro or {}).get("estado_conservacao") or ""
    if estado_atual not in estados:
        estados.append(estado_atual)
    valor_atual = (registro or {}).get("valor_aquisicao")
    valor_str = "" if valor_atual is None else str(valor_atual)
    data_atual = (registro or {}).get("data_aquisicao")
    try:
        data_inicial = date.fromisoformat(data_atual) if data_atual else None
    except (TypeError, ValueError):
        data_inicial = None

    with st.form(chave):
        if edicao:
            st.caption(f"Código patrimonial: {registro['codigo']} (não pode ser alterado)")
        else:
            st.caption("Código patrimonial: gerado automaticamente ao salvar (IPB-000001, ...)")
        descricao = st.text_input("Descrição do patrimônio *", value=(registro or {}).get("descricao") or "", max_chars=300)
        c1, c2 = st.columns(2)
        with c1:
            categoria_atual = (registro or {}).get("categoria_id") or ""
            categoria = st.selectbox(
                "Categoria", cat_ids,
                index=cat_ids.index(categoria_atual) if categoria_atual in cat_ids else 0,
                format_func=lambda x: categorias_map.get(x, "Não informada"),
            )
            subgrupo_atual = (registro or {}).get("subgrupo") or "Não informado"
            subgrupo = st.selectbox("Subgrupo do patrimônio", subgrupos, index=subgrupos.index(subgrupo_atual) if subgrupo_atual in subgrupos else 0)
            marca = st.text_input("Marca", value=(registro or {}).get("marca") or "")
            numero_serie = st.text_input("Número de série", value=(registro or {}).get("numero_serie") or "")
            estado = st.selectbox("Estado de conservação", estados, index=estados.index(estado_atual))
        with c2:
            local_atual = (registro or {}).get("localizacao_id") or ""
            local = st.selectbox(
                "Localização", loc_ids,
                index=loc_ids.index(local_atual) if local_atual in loc_ids else 0,
                format_func=lambda x: locais_map.get(x, "Não informada"),
            )
            modelo = st.text_input("Modelo", value=(registro or {}).get("modelo") or "")
            data_aquisicao = st.date_input("Data de aquisição", value=data_inicial, format="DD/MM/YYYY")
            valor_aquisicao = st.text_input("Valor de aquisição (R$)", value=valor_str, placeholder="Ex.: 1500,00")
        observacoes = st.text_area("Observações", value=(registro or {}).get("observacoes") or "")
        foto = st.file_uploader("Foto do patrimônio (opcional, JPG, PNG ou WEBP — até 5 MB)",
                                type=["jpg", "jpeg", "png", "webp"], key="foto_" + chave)
        nota_fiscal = st.file_uploader("Nota fiscal (opcional, PDF, JPG ou PNG — até 10 MB)",
                                      type=["pdf", "jpg", "jpeg", "png"], key="nf_" + chave)
        if edicao and registro.get("nota_fiscal_caminho"):
            st.caption("A nota fiscal atual será mantida se você não anexar outra.")
        if edicao and registro.get("foto_caminho"):
            st.caption("Se não selecionar outra imagem, a foto atual será mantida.")
        if edicao:
            st.caption("A situação (disponível/emprestado/manutenção) não é alterada aqui, para preservar o fluxo de empréstimos.")
        enviar = st.form_submit_button(
            "Salvar alterações" if edicao else "Cadastrar patrimônio",
            type="primary", use_container_width=True,
        )
    if not enviar:
        return
    if not descricao.strip():
        st.error("Informe a descrição do patrimônio.")
        return
    try:
        validar_foto(foto)
        validar_nota_fiscal(nota_fiscal)
    except ValueError as erro:
        st.error(str(erro))
        return
    try:
        payload = {
            "descricao": descricao.strip(),
            "categoria_id": id_opcional(categoria),
            "subgrupo": None if subgrupo == "Não informado" else subgrupo,
            "localizacao_id": id_opcional(local),
            "marca": marca.strip() or None,
            "modelo": modelo.strip() or None,
            "numero_serie": numero_serie.strip() or None,
            "data_aquisicao": data_opcional(data_aquisicao),
            "valor_aquisicao": decimal_opcional(valor_aquisicao),
            "estado_conservacao": estado or None,
            "observacoes": observacoes.strip() or None,
            "atualizado_por": st.session_state["user_id"],
        }
        api = api_usuario(st.session_state["access_token"])
        if edicao:
            payload["atualizado_em"] = "now()"  # substituído abaixo por ISO UTC
            from datetime import datetime, timezone
            payload["atualizado_em"] = datetime.now(timezone.utc).isoformat()
            resposta = api.from_("patrimonios").update(payload).eq("id", registro["id"]).execute()
            if not resposta.data:
                st.error("Nenhum registro foi atualizado. Verifique suas permissões RLS.")
                return
            if foto is not None:
                try:
                    salvar_foto_patrimonio(registro["id"], foto)
                except Exception as erro_foto:
                    st.warning(f"Dados atualizados, mas a foto não foi salva ({type(erro_foto).__name__}). Tente novamente em Editar patrimônio.")
                    return
            if nota_fiscal is not None:
                try:
                    salvar_nota_fiscal(registro["id"], nota_fiscal)
                except Exception as erro_nf:
                    st.warning(f"Dados atualizados, mas a nota fiscal não foi salva ({type(erro_nf).__name__}). Tente novamente em Editar patrimônio.")
                    return
            st.session_state["mensagem_patrimonio"] = "Patrimônio atualizado com sucesso!"
        else:
            # O trigger BEFORE INSERT do Supabase substitui este código temporário.
            # A coluna codigo é NOT NULL e não tem DEFAULT no esquema atual.
            payload["codigo"] = "PENDENTE"
            payload["criado_por"] = st.session_state["user_id"]
            resposta = api.from_("patrimonios").insert(payload).execute()
            if not resposta.data:
                st.error("O Supabase não retornou o patrimônio cadastrado.")
                return
            novo_id = resposta.data[0]["id"]
            if foto is not None:
                try:
                    salvar_foto_patrimonio(novo_id, foto)
                except Exception as erro_foto:
                    st.warning(f"Patrimônio cadastrado, mas a foto não foi salva ({type(erro_foto).__name__}). Abra Editar patrimônio para tentar novamente.")
                    return
            if nota_fiscal is not None:
                try:
                    salvar_nota_fiscal(novo_id, nota_fiscal)
                except Exception as erro_nf:
                    st.warning(f"Patrimônio cadastrado, mas a nota fiscal não foi salva ({type(erro_nf).__name__}). Abra Editar patrimônio para tentar novamente.")
                    return
            codigo = resposta.data[0].get("codigo", "")
            if codigo == "PENDENTE":
                st.warning("Cadastro realizado, mas o gatilho de numeração não atribuiu um código. Verifique o trigger no Supabase.")
            else:
                st.session_state["mensagem_patrimonio"] = f"Patrimônio cadastrado! Código: {codigo}"
        # A seleção será alterada ANTES da criação do radio na próxima execução.
        st.session_state["patrimonio_aba_pendente"] = "Consultar patrimônios"
        st.rerun()
    except ValueError as erro:
        st.error(str(erro))
    except Exception as erro:
        LOG.warning("Falha ao salvar patrimônio: %s", type(erro).__name__)
        st.error(f"Não foi possível concluir a operação ({type(erro).__name__}). Antes de tentar novamente, confira se o registro já aparece na consulta.")


def pagina_patrimonios(papel):
    st.header("Patrimônios")
    st.caption("Cadastro, consulta e edição de bens da igreja")
    try:
        categorias = listar_referencias("categorias")
        locais = listar_referencias("localizacoes")
        registros = listar_patrimonios()
    except Exception as erro:
        LOG.warning("Falha na consulta de patrimônios: %s", type(erro).__name__)
        st.error(f"Não foi possível consultar os dados ({type(erro).__name__}). Confira as políticas RLS e a conexão.")
        return

    pode_gerenciar = papel in ("admin", "gestor")
    abas = ["Consultar patrimônios"] + (["Cadastrar patrimônio", "Editar patrimônio"] if pode_gerenciar else []) + (["Excluir patrimônio"] if papel == "admin" else [])
    if st.session_state.get("mensagem_patrimonio"):
        st.success(st.session_state.pop("mensagem_patrimonio"))
    # Aplicar a mudança de aba antes de instanciar o widget.
    aba_pendente = st.session_state.pop("patrimonio_aba_pendente", None)
    if aba_pendente in abas:
        st.session_state["patrimonio_aba"] = aba_pendente
    aba = st.radio("Área de patrimônios", abas, horizontal=True, key="patrimonio_aba")
    if aba == "Consultar patrimônios":
        busca = st.text_input("Pesquisar", placeholder="Código, descrição, marca, modelo ou número de série")
        categorias_map = opcoes_referencia(categorias)
        locais_map = opcoes_referencia(locais)
        categorias_filtro = ["Todas"] + sorted(set(categorias_map.values()))
        subgrupos_filtro = ["Todos"] + ["SOM", "MÍDIA", "CONSELHO", "SAF", "MINISTÉRIO INFANTIL", "UME", "UPA", "UPH", "GRUPO DE MÚSICA"]
        situacoes_filtro = ["Todas"] + sorted({r.get("situacao") or "" for r in registros if r.get("situacao")})
        fc, fs, fg = st.columns(3)
        with fg:
            filtro_subgrupo = st.selectbox("Filtrar subgrupo", subgrupos_filtro)
        with fc:
            filtro_categoria = st.selectbox("Filtrar categoria", categorias_filtro)
        with fs:
            filtro_situacao = st.selectbox("Filtrar situação", situacoes_filtro)
        filtrados = []
        for r in registros:
            campos = " ".join(str(r.get(k) or "") for k in ("codigo", "descricao", "marca", "modelo", "numero_serie"))
            if busca.casefold() not in campos.casefold():
                continue
            if filtro_categoria != "Todas" and categorias_map.get(r.get("categoria_id")) != filtro_categoria:
                continue
            if filtro_situacao != "Todas" and r.get("situacao") != filtro_situacao:
                continue
            if filtro_subgrupo != "Todos" and r.get("subgrupo") != filtro_subgrupo:
                continue
            filtrados.append({
                "Código": r.get("codigo"),
                "Descrição": r.get("descricao"),
                "Categoria": categorias_map.get(r.get("categoria_id"), "—"),
                "Subgrupo": r.get("subgrupo") or "—",
                "Localização": locais_map.get(r.get("localizacao_id"), "—"),
                "Marca": r.get("marca") or "—",
                "Situação": r.get("situacao") or "—",
                "Conservação": r.get("estado_conservacao") or "—",
            })
        st.caption(f"{len(filtrados)} patrimônio(s) encontrado(s)")
        st.dataframe(filtrados, use_container_width=True, hide_index=True)
        if registros:
            st.markdown("#### Visualizar foto de um patrimônio")
            por_id_foto = {r["id"]: r for r in registros}
            foto_id = st.selectbox("Selecione o bem", list(por_id_foto),
                format_func=lambda i: f"{por_id_foto[i].get('codigo','')} — {por_id_foto[i].get('descricao','')}",
                key="visualizar_foto_bem")
            exibir_foto_patrimonio(por_id_foto[foto_id])
            st.markdown("#### Nota fiscal do patrimônio")
            exibir_nota_fiscal(por_id_foto[foto_id])
    if aba == "Excluir patrimônio" and papel == "admin":
        st.subheader("Excluir patrimônio")
        st.warning("A exclusão é definitiva. Bens com histórico de empréstimos ou documentos vinculados não podem ser excluídos por esta tela.")
        if not registros:
            st.info("Não há patrimônios cadastrados para excluir.")
        else:
            por_id_exclusao = {r["id"]: r for r in registros}
            id_exclusao = st.selectbox(
                "Selecione o patrimônio que deseja excluir",
                list(por_id_exclusao),
                format_func=lambda i: f"{por_id_exclusao[i].get('codigo', '')} — {por_id_exclusao[i].get('descricao', '')}",
                key="patrimonio_excluir_id",
            )
            bem_exclusao = por_id_exclusao[id_exclusao]
            st.write(f"**Código:** {bem_exclusao.get('codigo') or '—'}")
            st.write(f"**Descrição:** {bem_exclusao.get('descricao') or '—'}")
            confirmar_exclusao = st.checkbox(
                "Confirmo que desejo excluir definitivamente este patrimônio.",
                key=f"confirmar_exclusao_{id_exclusao}",
            )
            if st.button("Excluir patrimônio definitivamente", type="primary",
                         disabled=not confirmar_exclusao, key="executar_exclusao_patrimonio"):
                try:
                    cliente = api_usuario(st.session_state["access_token"])
                    itens_vinculados = (cliente.from_("itens_emprestimo")
                        .select("id").eq("patrimonio_id", id_exclusao).limit(1).execute()).data or []
                    anexos_vinculados = (cliente.from_("anexos_ipb")
                        .select("id").eq("patrimonio_id", id_exclusao).limit(1).execute()).data or []
                    if itens_vinculados or anexos_vinculados:
                        st.error("Exclusão bloqueada: este patrimônio possui empréstimos ou documentos vinculados. Preserve o histórico.")
                    else:
                        resposta_exclusao = (cliente.from_("patrimonios")
                            .delete().eq("id", id_exclusao).select("id").execute())
                        if resposta_exclusao.data:
                            st.session_state["mensagem_patrimonio"] = "Patrimônio excluído com sucesso."
                            st.session_state["patrimonio_aba_pendente"] = "Consultar patrimônios"
                            st.rerun()
                        else:
                            st.error("A exclusão não foi confirmada pelo banco. Verifique as permissões do administrador (RLS).")
                except Exception as erro:
                    LOG.warning("Falha ao excluir patrimônio: %s", type(erro).__name__)
                    st.error(f"Não foi possível excluir o patrimônio ({type(erro).__name__}). Verifique vínculos e permissões do banco.")
    if pode_gerenciar:
        if aba == "Cadastrar patrimônio":
            formulario_patrimonio("form_cadastro_patrimonio", categorias, locais)
        if aba == "Editar patrimônio":
            if not registros:
                st.info("Ainda não existem patrimônios cadastrados.")
            else:
                por_id = {r["id"]: r for r in registros}
                selecionado = st.selectbox(
                    "Selecione o patrimônio para editar",
                    list(por_id),
                    format_func=lambda id_: f"{por_id[id_].get('codigo', '')} — {por_id[id_].get('descricao', '')}",
                )
                formulario_patrimonio("form_edicao_" + selecionado, categorias, locais, por_id[selecionado])



def listar_pessoas():
    resposta = api_usuario(st.session_state["access_token"]).from_("pessoas").select("id,tipo,nome,documento,telefone,email,endereco,observacoes").order("nome").execute()
    return resposta.data or []


def listar_emprestimos():
    resposta = api_usuario(st.session_state["access_token"]).from_("emprestimos").select("id,numero,pessoa_id,data_retirada,data_prevista_devolucao,finalidade,responsavel_entrega,responsavel_recebimento,status,observacoes,criado_em").order("numero", desc=True).limit(500).execute()
    return resposta.data or []


def recibo_emprestimo_pdf(emprestimo, pessoa, bens):
    """Recibo A4 para assinatura na retirada e na devolução, inclusive manual."""
    from io import BytesIO
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
    )

    verde = colors.HexColor("#075039")
    cinza = colors.HexColor("#52645A")
    fundo = colors.HexColor("#EAF3ED")
    saida = BytesIO()
    doc = SimpleDocTemplate(
        saida, pagesize=A4, rightMargin=1.65*cm, leftMargin=1.65*cm,
        topMargin=1.45*cm, bottomMargin=1.45*cm
    )
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle(
        name="IPBInstituicao", parent=estilos["Normal"], alignment=TA_CENTER,
        fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=verde,
        spaceAfter=4
    ))
    estilos.add(ParagraphStyle(
        name="IPBSubtituloRecibo", parent=estilos["Normal"], alignment=TA_CENTER,
        fontSize=11, leading=15, textColor=cinza, spaceAfter=11
    ))
    estilos.add(ParagraphStyle(
        name="IPBSecaoRecibo", parent=estilos["Normal"], fontName="Helvetica-Bold",
        fontSize=10, leading=13, textColor=verde, spaceBefore=11, spaceAfter=7
    ))
    estilos.add(ParagraphStyle(
        name="IPBTextoRecibo", parent=estilos["Normal"], fontSize=9, leading=13,
        textColor=colors.HexColor("#263B31"), spaceAfter=5
    ))
    estilos.add(ParagraphStyle(
        name="IPBTextoCentroRecibo", parent=estilos["IPBTextoRecibo"],
        alignment=TA_CENTER, spaceAfter=0
    ))
    estilos.add(ParagraphStyle(
        name="IPBAssinaturaNome", parent=estilos["Normal"], alignment=TA_CENTER,
        fontName="Helvetica-Bold", fontSize=9, leading=12, spaceAfter=2
    ))
    estilos.add(ParagraphStyle(
        name="IPBAssinaturaFuncao", parent=estilos["Normal"], alignment=TA_CENTER,
        fontSize=8, leading=11, textColor=cinza
    ))

    def p(valor, estilo="IPBTextoRecibo"):
        return Paragraph(escape(str(valor if valor not in (None, "") else "—")), estilos[estilo])

    def campo(rotulo, valor):
        return Paragraph(
            f"<b>{escape(rotulo)}:</b> {escape(str(valor if valor not in (None, '') else '—'))}",
            estilos["IPBTextoRecibo"]
        )

    def assinaturas(nome_esquerda, funcao_esquerda, nome_direita, funcao_direita):
        def coluna(nome, funcao):
            return [
                Spacer(1, .68*cm),
                p("____________________________________", "IPBTextoCentroRecibo"),
                p(nome or "Nome: __________________________", "IPBAssinaturaNome"),
                p(funcao, "IPBAssinaturaFuncao"),
            ]
        tabela = Table([[
            coluna(nome_esquerda, funcao_esquerda),
            coluna(nome_direita, funcao_direita),
        ]], colWidths=[8.45*cm, 8.45*cm])
        tabela.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        return KeepTogether(tabela)

    numero = emprestimo.get("numero", "—")
    conteudo = [
        p("PRIMEIRA IGREJA PRESBITERIANA DO CABO", "IPBInstituicao"),
        p(f"RECIBO DE EMPRÉSTIMO PATRIMONIAL Nº {numero}", "IPBSubtituloRecibo"),
        HRFlowable(width="100%", thickness=1.4, color=verde),
        p("01  |  IDENTIFICAÇÃO DO EMPRÉSTIMO", "IPBSecaoRecibo"),
        campo("Pessoa / instituição que retira", pessoa.get("nome")),
        campo("Documento", pessoa.get("documento") or "Não informado"),
        campo("Telefone", pessoa.get("telefone") or "Não informado"),
        campo("Data da retirada", emprestimo.get("data_retirada")),
        campo("Previsão de devolução", emprestimo.get("data_prevista_devolucao") or "Não definida"),
        campo("Finalidade", emprestimo.get("finalidade") or "Não informada"),
        p("02  |  BENS ENTREGUES", "IPBSecaoRecibo"),
    ]
    linhas = [[p("CÓDIGO"), p("DESCRIÇÃO"), p("CONSERVAÇÃO")]]
    for bem in bens:
        linhas.append([
            p(bem.get("codigo")),
            p(bem.get("descricao")),
            p(bem.get("estado_conservacao") or "Não informado"),
        ])
    tabela_bens = Table(
        linhas, colWidths=[3.15*cm, 10.05*cm, 3.7*cm],
        repeatRows=1, hAlign="CENTER"
    )
    tabela_bens.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), fundo),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#B7C9BD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    conteudo.extend([
        tabela_bens,
        Spacer(1, .22*cm),
        campo("Observações", emprestimo.get("observacoes") or "Nenhuma"),
        p("03  |  CONFIRMAÇÃO DA RETIRADA", "IPBSecaoRecibo"),
        p("Declaro que os bens acima foram entregues e recebidos, comprometendo-me a devolvê-los nas condições acordadas."),
        assinaturas(
            emprestimo.get("responsavel_entrega"), "Quem entregou os bens",
            emprestimo.get("responsavel_recebimento") or pessoa.get("nome"),
            "Quem recebeu os bens",
        ),
        Spacer(1, .35*cm),
        HRFlowable(width="100%", thickness=.7, color=colors.HexColor("#B7C9BD")),
        p("04  |  REGISTRO DA DEVOLUÇÃO", "IPBSecaoRecibo"),
        p("Data da devolução: ______ / ______ / __________"),
        p("Condição dos bens na devolução:  (   ) Boa    (   ) Regular    (   ) Necessita manutenção"),
        p("Observações da devolução: __________________________________________________________"),
        Spacer(1, .15*cm),
        assinaturas(
            pessoa.get("nome"), "Quem devolveu os bens",
            None, "Quem recebeu a devolução",
        ),
        Spacer(1, .28*cm),
        p("Em devoluções parciais, registre os itens efetivamente devolvidos no sistema e anexe o comprovante assinado.", "IPBTextoRecibo"),
    ])
    doc.build(conteudo)
    return saida.getvalue()


st.markdown("""<style>
    /* Mesmo padrão para os menus internos de patrimônios, empréstimos e devoluções. */
    :is(.st-key-patrimonio_aba, .st-key-emprestimo_aba, .st-key-devolucao_aba) [role="radiogroup"] {
        display: flex !important; flex-flow: row nowrap !important;
        gap: 6px !important; width: 100% !important;
    }
    :is(.st-key-patrimonio_aba, .st-key-emprestimo_aba, .st-key-devolucao_aba) [role="radiogroup"] label {
        flex: 1 1 0 !important; min-width: 0 !important;
        display: flex !important; align-items: center !important;
        justify-content: center !important;
        padding: 10px 5px !important; border: 1px solid #43816b !important;
        border-radius: 9px !important; background: #0b4b39 !important;
        margin: 0 !important;
    }
    :is(.st-key-patrimonio_aba, .st-key-emprestimo_aba, .st-key-devolucao_aba) [role="radiogroup"] label:has(input:checked) {
        background: #147d55 !important; border-color: #8de0b2 !important;
    }
    :is(.st-key-patrimonio_aba, .st-key-emprestimo_aba, .st-key-devolucao_aba) [role="radiogroup"] label [data-baseweb="radio"] {display:none !important;}
    :is(.st-key-patrimonio_aba, .st-key-emprestimo_aba, .st-key-devolucao_aba) [role="radiogroup"] label p {
        font-size: clamp(11px, 1.05vw, 15px) !important;
        font-weight: 650 !important; color: white !important;
        white-space: nowrap !important;
    }
    @media (max-width: 768px) {
        :is(.st-key-patrimonio_aba, .st-key-emprestimo_aba, .st-key-devolucao_aba) [role="radiogroup"] {
            overflow-x: auto !important; padding-bottom: 5px !important;
        }
        :is(.st-key-patrimonio_aba, .st-key-emprestimo_aba, .st-key-devolucao_aba) [role="radiogroup"] label {
            flex: 0 0 auto !important; padding: 9px 10px !important;
        }
        :is(.st-key-patrimonio_aba, .st-key-emprestimo_aba, .st-key-devolucao_aba) [role="radiogroup"] label p {
            font-size: 13px !important;
        }
    }
    </style>""", unsafe_allow_html=True)

def pagina_emprestimos(papel, nome_usuario):
    st.header("Empréstimos")
    st.caption("Registro, acompanhamento e emissão de recibos para assinatura em papel")
    pode_gerenciar = papel in ("admin", "gestor")
    try:
        pessoas = listar_pessoas()
        bens = listar_patrimonios()
        emprestimos = listar_emprestimos()
    except Exception as erro:
        LOG.warning("Erro ao consultar empréstimos: %s", type(erro).__name__)
        st.error(f"Não foi possível carregar os dados ({type(erro).__name__}).")
        return

    if st.session_state.get("mensagem_emprestimo"):
        st.success(st.session_state.pop("mensagem_emprestimo"))
    opcoes = ["Empréstimos registrados", "Emitir recibo"]
    if pode_gerenciar:
        opcoes = ["Novo empréstimo"] + opcoes
    aba_pendente = st.session_state.pop("emprestimo_aba_pendente", None)
    if aba_pendente in opcoes:
        st.session_state["emprestimo_aba"] = aba_pendente
    aba = st.radio("Área de empréstimos", opcoes, horizontal=True, key="emprestimo_aba")
    pessoas_map = {p["id"]: p for p in pessoas}
    bens_map = {b["id"]: b for b in bens}

    if aba == "Novo empréstimo":
        disponiveis = [b for b in bens if b.get("situacao") == "disponivel"]
        if not disponiveis:
            st.info("Não existem patrimônios disponíveis para empréstimo.")
        else:
            with st.form("novo_emprestimo_ipb"):
                st.subheader("Dados de quem recebe o empréstimo")
                tipo_pessoa = st.selectbox("Tipo de recebedor", ["pessoa_fisica", "organizacao"], format_func=lambda v: "Pessoa física" if v == "pessoa_fisica" else "Organização")
                nome_pessoa = st.text_input("Nome completo ou organização *")
                cdoc, ctel = st.columns(2)
                with cdoc:
                    documento_pessoa = st.text_input("CPF/CNPJ (opcional)")
                with ctel:
                    telefone_pessoa = st.text_input("Telefone (opcional)")
                email_pessoa = st.text_input("E-mail (opcional)")
                endereco_pessoa = st.text_input("Endereço (opcional)")
                ids = st.multiselect("Selecione um ou mais patrimônios disponíveis *", [b["id"] for b in disponiveis], format_func=lambda i: f"{bens_map[i]['codigo']} — {bens_map[i]['descricao']}")
                c1, c2 = st.columns(2)
                with c1:
                    retirada = st.date_input("Data de retirada *", value=date.today(), format="DD/MM/YYYY")
                    entrega = st.text_input("Responsável pela entrega *", value=nome_usuario)
                with c2:
                    prevista = st.date_input("Previsão de devolução", value=None, format="DD/MM/YYYY")
                    recebimento = st.text_input("Responsável pelo recebimento *", value="")
                finalidade = st.text_area("Finalidade do empréstimo")
                observacoes = st.text_area("Observações")
                enviar = st.form_submit_button("Registrar empréstimo", type="primary", use_container_width=True)
            if enviar:
                if not ids or not nome_pessoa.strip() or not entrega.strip() or not recebimento.strip():
                    st.error("Informe o nome de quem recebe, selecione os bens e preencha os responsáveis pela entrega e recebimento.")
                elif prevista and prevista < retirada:
                    st.error("A previsão de devolução não pode ser anterior à retirada.")
                else:
                    try:
                        # O banco existente exige pessoa_id. O cadastro é realizado
                        # automaticamente, sem uma tela separada de pessoas.
                        dados_pessoa = {
                            "tipo": tipo_pessoa, "nome": nome_pessoa.strip(),
                            "documento": documento_pessoa.strip() or None,
                            "telefone": telefone_pessoa.strip() or None,
                            "email": email_pessoa.strip() or None,
                            "endereco": endereco_pessoa.strip() or None,
                            "criado_por": st.session_state["user_id"],
                        }
                        pessoa_criada = (api_usuario(st.session_state["access_token"])
                            .from_("pessoas").insert(dados_pessoa).execute())
                        if not pessoa_criada.data:
                            raise ValueError("Não foi possível salvar os dados do recebedor")
                        pessoa_id = pessoa_criada.data[0]["id"]
                        resposta = api_usuario(st.session_state["access_token"]).rpc("registrar_emprestimo_ipb", {
                            "p_pessoa_id": pessoa_id,
                            "p_patrimonio_ids": ids,
                            "p_data_retirada": retirada.isoformat(),
                            "p_data_prevista_devolucao": prevista.isoformat() if prevista else None,
                            "p_finalidade": finalidade.strip(),
                            "p_responsavel_entrega": entrega.strip(),
                            "p_responsavel_recebimento": recebimento.strip(),
                            "p_observacoes": observacoes.strip(),
                        }).execute()
                        resultado = resposta.data
                        if not isinstance(resultado, dict) or "numero" not in resultado:
                            raise ValueError("O Supabase não confirmou o número do empréstimo")
                    except Exception as erro:
                        # Mostrar o erro estruturado do PostgREST sem registrar tokens,
                        # cabeçalhos de autenticação ou o conteúdo completo da exceção.
                        codigo_erro = getattr(erro, "code", None)
                        mensagem_erro = getattr(erro, "message", None)
                        detalhes_erro = getattr(erro, "details", None)
                        # Algumas versões da biblioteca guardam esses campos em um dicionário.
                        if not mensagem_erro and getattr(erro, "args", None):
                            primeiro = erro.args[0]
                            if isinstance(primeiro, dict):
                                codigo_erro = codigo_erro or primeiro.get("code")
                                mensagem_erro = primeiro.get("message")
                                detalhes_erro = detalhes_erro or primeiro.get("details")
                        LOG.error(
                            "Falha ao registrar empréstimo: tipo=%s codigo=%s mensagem=%s detalhes=%s",
                            type(erro).__name__, codigo_erro, mensagem_erro, detalhes_erro,
                        )
                        st.error("Não foi possível confirmar o empréstimo. Confira a lista antes de tentar novamente.")
                        if codigo_erro:
                            st.code(f"Código do Supabase: {codigo_erro}")
                        if mensagem_erro:
                            st.warning(f"Mensagem do Supabase: {mensagem_erro}")
                        st.caption("Se enviar uma captura da mensagem, oculte nomes, documentos, chaves e tokens.")
                    else:
                        st.session_state["mensagem_emprestimo"] = f"Empréstimo nº {resultado['numero']} registrado com sucesso!"
                        st.session_state["emprestimo_aba_pendente"] = "Novo empréstimo"
                        st.session_state["recibo_novo_numero"] = resultado["numero"]
                        st.rerun()

        # Após salvar, o recibo aparece aqui, na própria tela de registro.
        numero_recibo = st.session_state.get("recibo_novo_numero")
        if numero_recibo is not None:
            st.divider()
            st.subheader(f"Recibo do empréstimo nº {numero_recibo}")
            st.success("Empréstimo salvo. O recibo está disponível abaixo para impressão e assinatura.")
            try:
                registro = next((e for e in listar_emprestimos() if str(e.get("numero")) == str(numero_recibo)), None)
                if registro is None:
                    st.warning("O empréstimo foi salvo, mas ainda não foi possível carregar o recibo. Consulte a opção Emitir recibo.")
                else:
                    dados_recebedor = (api_usuario(st.session_state["access_token"])
                        .from_("pessoas").select("*").eq("id", registro["pessoa_id"]).single().execute()).data
                    itens = (api_usuario(st.session_state["access_token"])
                        .from_("itens_emprestimo").select("patrimonio_id")
                        .eq("emprestimo_id", registro["id"]).execute()).data or []
                    bens_atualizados = {b["id"]: b for b in listar_patrimonios()}
                    bens_recibo = [bens_atualizados[i["patrimonio_id"]] for i in itens if i["patrimonio_id"] in bens_atualizados]
                    if not bens_recibo or len(bens_recibo) != len(itens):
                        st.warning("Não foi possível carregar todos os itens do recibo.")
                    else:
                        pdf = recibo_emprestimo_pdf(registro, dados_recebedor, bens_recibo)
                        st.download_button("Baixar recibo em PDF", data=pdf,
                            file_name=f"recibo_emprestimo_{numero_recibo}.pdf",
                            mime="application/pdf", type="primary", use_container_width=True,
                            key=f"recibo_apos_salvar_{numero_recibo}")
            except Exception as erro:
                LOG.warning("Erro ao preparar recibo após salvar: %s", type(erro).__name__)
                st.warning("Empréstimo salvo, mas não foi possível gerar o PDF agora. Use a opção Emitir recibo.")

    elif aba == "Empréstimos registrados":
        linhas = []
        for e in emprestimos:
            linhas.append({"Número": e["numero"], "Recebedor": pessoas_map.get(e["pessoa_id"], {}).get("nome", "—"), "Retirada": e.get("data_retirada"), "Previsão": e.get("data_prevista_devolucao") or "—", "Status": e.get("status")})
        st.caption(f"{len(linhas)} empréstimo(s) listado(s) — últimos 500")
        st.dataframe(linhas, use_container_width=True, hide_index=True)

    elif aba == "Emitir recibo":
        if not emprestimos:
            st.info("Ainda não existem empréstimos cadastrados.")
        else:
            por_numero = {e["numero"]: e for e in emprestimos}
            numeros = list(por_numero)
            preferido = st.session_state.pop("recibo_numero_pendente", None)
            numero = st.selectbox("Selecione o empréstimo", numeros, index=numeros.index(preferido) if preferido in numeros else 0, format_func=lambda n: f"Empréstimo nº {n} — {pessoas_map.get(por_numero[n]['pessoa_id'], {}).get('nome', '—')}")
            emprestimo = por_numero[numero]
            try:
                resposta = api_usuario(st.session_state["access_token"]).from_("itens_emprestimo").select("patrimonio_id").eq("emprestimo_id", emprestimo["id"]).execute()
                ids = [i["patrimonio_id"] for i in (resposta.data or [])]
                bens_recibo = [bens_map[i] for i in ids if i in bens_map]
                if len(bens_recibo) != len(ids) or not ids:
                    st.warning("Não foi possível identificar todos os bens deste empréstimo.")
                elif emprestimo["pessoa_id"] not in pessoas_map:
                    st.warning("Pessoa associada ao empréstimo não encontrada.")
                else:
                    pdf = recibo_emprestimo_pdf(emprestimo, pessoas_map[emprestimo["pessoa_id"]], bens_recibo)
                    st.download_button("Baixar recibo em PDF", data=pdf, file_name=f"recibo_emprestimo_{numero}.pdf", mime="application/pdf", type="primary", use_container_width=True)
                    st.caption("Imprima o recibo e recolha as assinaturas em papel. O PDF é gerado sob demanda e não é anexado automaticamente ao Supabase.")
            except ImportError:
                st.error("A biblioteca reportlab não está instalada. Adicione reportlab ao requirements.txt do GitHub.")
            except Exception as erro:
                LOG.warning("Falha ao gerar recibo: %s", type(erro).__name__)
                st.error(f"Não foi possível gerar o recibo ({type(erro).__name__}).")



def listar_itens_devolucao(emprestimo_id):
    resposta = (api_usuario(st.session_state["access_token"])
        .from_("itens_emprestimo")
        .select("id,emprestimo_id,patrimonio_id,data_devolucao,estado_na_retirada,estado_na_devolucao,responsavel_devolucao,observacoes")
        .eq("emprestimo_id", emprestimo_id).execute())
    return resposta.data or []


def pagina_devolucoes(papel, nome_usuario):
    st.header("Devoluções")
    st.caption("Devolução total ou parcial, com histórico por patrimônio")
    pode_gerenciar = papel in ("admin", "gestor")
    try:
        emprestimos = listar_emprestimos()
        pessoas = {p["id"]: p for p in listar_pessoas()}
        bens = {p["id"]: p for p in listar_patrimonios()}
    except Exception as erro:
        LOG.warning("Falha ao consultar devoluções: %s", type(erro).__name__)
        st.error("Não foi possível carregar as devoluções. Confira a conexão e as permissões.")
        return

    if st.session_state.get("mensagem_devolucao"):
        st.success(st.session_state.pop("mensagem_devolucao"))

    ativos = [e for e in emprestimos if e.get("status") == "ativo"]
    abas = ["Empréstimos pendentes", "Histórico de devoluções"]
    if pode_gerenciar:
        abas.insert(0, "Registrar devolução")
    aba_pendente = st.session_state.pop("devolucao_aba_pendente", None)
    if aba_pendente in abas:
        st.session_state["devolucao_aba"] = aba_pendente
    aba = st.radio("Área de devoluções", abas, horizontal=True, key="devolucao_aba")

    if aba == "Empréstimos pendentes":
        linhas = [{"Empréstimo": e["numero"],
                   "Recebedor": pessoas.get(e["pessoa_id"], {}).get("nome", "—"),
                   "Retirada": e.get("data_retirada"),
                   "Previsão": e.get("data_prevista_devolucao") or "—"}
                  for e in ativos]
        st.caption(f"{len(linhas)} empréstimo(s) ativo(s)")
        st.dataframe(linhas, use_container_width=True, hide_index=True)

    elif aba == "Registrar devolução":
        if not ativos:
            st.info("Não existem empréstimos ativos para devolução.")
            return
        por_id = {e["id"]: e for e in ativos}
        emprestimo_id = st.selectbox(
            "Empréstimo ativo", list(por_id),
            format_func=lambda i: f"Nº {por_id[i]['numero']} — {pessoas.get(por_id[i]['pessoa_id'], {}).get('nome', '—')}")
        emprestimo = por_id[emprestimo_id]
        try:
            itens = listar_itens_devolucao(emprestimo_id)
        except Exception as erro:
            LOG.warning("Falha ao consultar itens de devolução: %s", type(erro).__name__)
            st.error("Não foi possível consultar os itens deste empréstimo.")
            return
        pendentes = [i for i in itens if i.get("data_devolucao") is None]
        if not pendentes:
            st.info("Todos os itens deste empréstimo já foram devolvidos.")
            return
        por_item = {i["id"]: i for i in pendentes}
        def descricao_item(i):
            b = bens.get(por_item[i]["patrimonio_id"], {})
            return f"{b.get('codigo', '—')} — {b.get('descricao', 'Patrimônio')}"
        st.caption(f"{len(pendentes)} item(ns) aguardando devolução")
        with st.form("form_devolucao_ipb"):
            selecionados = st.multiselect("Patrimônios recebidos *", list(por_item),
                                         default=list(por_item), format_func=descricao_item)
            col1, col2 = st.columns(2)
            with col1:
                data_devolucao = st.date_input("Data de devolução *", value=date.today(), format="DD/MM/YYYY")
                responsavel = st.text_input("Responsável pelo recebimento *", value=nome_usuario)
            with col2:
                estado = st.selectbox("Estado dos bens devolvidos", ["Não alterar", "Novo", "Bom", "Regular", "Ruim"])
                st.caption("Estado Ruim encaminha o patrimônio para manutenção.")
            observacoes = st.text_area("Observações da devolução")
            enviar = st.form_submit_button("Confirmar devolução", type="primary", use_container_width=True)
        if enviar:
            if not selecionados or not responsavel.strip():
                st.error("Selecione os patrimônios e informe o responsável.")
            elif data_devolucao < date.fromisoformat(emprestimo["data_retirada"]):
                st.error("A data de devolução não pode ser anterior à retirada.")
            else:
                try:
                    resposta = api_usuario(st.session_state["access_token"]).rpc(
                        "registrar_devolucao_ipb", {
                            "p_emprestimo_id": emprestimo_id,
                            "p_item_ids": selecionados,
                            "p_data_devolucao": data_devolucao.isoformat(),
                            "p_responsavel_devolucao": responsavel.strip(),
                            "p_estado_na_devolucao": None if estado == "Não alterar" else estado,
                            "p_observacoes": observacoes.strip() or None,
                        }).execute()
                    if not isinstance(resposta.data, dict) or "quantidade_devolvida" not in resposta.data:
                        raise ValueError("O banco não confirmou a devolução")
                except Exception as erro:
                    LOG.warning("Falha ao registrar devolução: tipo=%s codigo=%s mensagem=%s",
                                type(erro).__name__, getattr(erro, "code", None), getattr(erro, "message", None))
                    st.error("Não foi possível confirmar a devolução. Confira o histórico antes de tentar novamente.")
                    if getattr(erro, "code", None):
                        st.code(f"Código do Supabase: {erro.code}")
                    if getattr(erro, "message", None):
                        st.warning(f"Mensagem do Supabase: {erro.message}")
                else:
                    resultado = resposta.data
                    st.session_state["mensagem_devolucao"] = (
                        f"Devolução registrada: {resultado['quantidade_devolvida']} bem(ns). "
                        f"Restantes: {resultado['quantidade_pendente']}.")
                    st.session_state["devolucao_aba_pendente"] = "Histórico de devoluções"
                    st.rerun()

    elif aba == "Histórico de devoluções":
        linhas = []
        for e in emprestimos:
            try:
                itens = listar_itens_devolucao(e["id"])
            except Exception as erro:
                LOG.warning("Falha ao consultar histórico: %s", type(erro).__name__)
                st.error("Não foi possível carregar o histórico completo.")
                return
            for i in itens:
                if i.get("data_devolucao"):
                    bem = bens.get(i["patrimonio_id"], {})
                    linhas.append({
                        "Empréstimo": e["numero"], "Código": bem.get("codigo", "—"),
                        "Patrimônio": bem.get("descricao", "—"),
                        "Data de devolução": i["data_devolucao"],
                        "Estado na devolução": i.get("estado_na_devolucao") or "—",
                        "Responsável": i.get("responsavel_devolucao") or "—",
                        "Observações": i.get("observacoes") or "—",
                    })
        st.caption(f"{len(linhas)} bem(ns) devolvido(s) — empréstimos mais recentes")
        st.dataframe(linhas, use_container_width=True, hide_index=True)
        st.info("Anexos de recibos assinados serão habilitados após configurar um bucket privado no Supabase Storage.")




# Documentos privados: nunca utilizar a chave service_role no aplicativo.
BUCKET_RECIBOS = "ipb-recibos"
TAMANHO_MAXIMO = 10 * 1024 * 1024


def requisicao_storage(metodo, caminho, dados=None, tipo=None):
    base = st.secrets["SUPABASE_URL"].rstrip("/")
    url = base + "/storage/v1/object/" + BUCKET_RECIBOS + "/" + quote(caminho, safe="/")
    headers = {
        "apikey": st.secrets["SUPABASE_ANON_KEY"],
        "Authorization": "Bearer " + st.session_state["access_token"],
    }
    if tipo:
        headers["Content-Type"] = tipo
    if metodo == "POST":
        headers["x-upsert"] = "false"
    req = Request(url, data=dados, headers=headers, method=metodo)
    with urlopen(req, timeout=40) as resp:
        return resp.read()


def listar_anexos_ipb(emprestimo_id=None, patrimonio_id=None):
    consulta = (api_usuario(st.session_state["access_token"])
                .from_("anexos_ipb")
                .select("id,emprestimo_id,patrimonio_id,tipo,caminho,nome_arquivo,mime_type,tamanho_bytes,criado_em")
                .order("criado_em", desc=True).limit(500))
    if emprestimo_id:
        consulta = consulta.eq("emprestimo_id", emprestimo_id)
    if patrimonio_id:
        consulta = consulta.eq("patrimonio_id", patrimonio_id)
    return consulta.execute().data or []


def pagina_documentos(papel):
    st.header("Documentos assinados")
    st.caption("Recibos de empréstimos e devoluções em armazenamento privado")
    try:
        emprestimos = listar_emprestimos()
        bens = listar_patrimonios()
        pessoas = {p["id"]: p for p in listar_pessoas()}
    except Exception as erro:
        st.error(f"Não foi possível carregar os dados ({type(erro).__name__}).")
        return
    if not emprestimos:
        st.info("Ainda não existem empréstimos cadastrados.")
        return
    por_id = {e["id"]: e for e in emprestimos}
    emprestimo_id = st.selectbox("Empréstimo", list(por_id),
        format_func=lambda i: f"Nº {por_id[i]['numero']} — {pessoas.get(por_id[i]['pessoa_id'], {}).get('nome','—')}")
    relacionados = []
    try:
        resposta = (api_usuario(st.session_state["access_token"])
                    .from_("itens_emprestimo").select("patrimonio_id")
                    .eq("emprestimo_id", emprestimo_id).execute())
        ids = {x["patrimonio_id"] for x in (resposta.data or [])}
        relacionados = [b for b in bens if b["id"] in ids]
    except Exception as erro:
        st.error(f"Falha ao consultar os bens ({type(erro).__name__}).")
        return
    if papel in ("admin", "gestor"):
        st.subheader("Anexar comprovante")
        with st.form("form_anexo_ipb", clear_on_submit=True):
            tipo = st.selectbox("Tipo de comprovante", ["emprestimo", "devolucao"],
                format_func=lambda x: "Recibo de empréstimo" if x == "emprestimo" else "Comprovante de devolução")
            escolhas = [""] + [b["id"] for b in relacionados]
            mapa = {b["id"]: b for b in relacionados}
            patrimonio_id = st.selectbox("Patrimônio vinculado (opcional)", escolhas,
                format_func=lambda x: "Empréstimo completo (todos os bens)" if not x else f"{mapa[x]['codigo']} — {mapa[x]['descricao']}")
            arquivo = st.file_uploader("Arquivo assinado (PDF, JPG ou PNG, até 10 MB)", type=["pdf","jpg","jpeg","png"])
            enviar = st.form_submit_button("Salvar comprovante", type="primary", use_container_width=True)
        if enviar:
            if arquivo is None:
                st.warning("Selecione um arquivo.")
            else:
                dados = arquivo.getvalue()
                extensao = Path(arquivo.name).suffix.lower()
                mime = {".pdf":"application/pdf", ".jpg":"image/jpeg", ".jpeg":"image/jpeg", ".png":"image/png"}.get(extensao)
                assinatura = dados[:8]
                valido = (mime == "application/pdf" and assinatura.startswith(b"%PDF-")) or (mime == "image/png" and assinatura == b"\x89PNG\r\n\x1a\n") or (mime == "image/jpeg" and assinatura[:3] == b"\xff\xd8\xff")
                if not mime or not valido:
                    st.error("Formato inválido. Envie um PDF, JPG ou PNG válido.")
                elif not dados or len(dados) > TAMANHO_MAXIMO:
                    st.error("O arquivo precisa ter entre 1 byte e 10 MB.")
                else:
                    caminho = f"{emprestimo_id}/{uuid.uuid4().hex}{extensao}"
                    try:
                        requisicao_storage("POST", caminho, dados, mime)
                    except Exception as erro:
                        LOG.warning("Erro ao enviar documento: %s", type(erro).__name__)
                        st.error("Falha no envio ao Storage. Confira as políticas e o bucket.")
                    else:
                        try:
                            api_usuario(st.session_state["access_token"]).from_("anexos_ipb").insert({
                                "emprestimo_id": emprestimo_id,
                                "patrimonio_id": patrimonio_id or None,
                                "tipo": tipo, "caminho": caminho,
                                "nome_arquivo": Path(arquivo.name).name[:240],
                                "mime_type": mime, "tamanho_bytes": len(dados),
                                "criado_por": st.session_state["user_id"],
                            }).execute()
                        except Exception as erro:
                            LOG.warning("Falha ao registrar anexo: %s", type(erro).__name__)
                            try:
                                requisicao_storage("DELETE", caminho)
                            except Exception:
                                LOG.warning("Arquivo órfão no Storage após falha no cadastro")
                            st.error("Arquivo enviado, mas não foi possível registrar o comprovante. Confira as permissões.")
                        else:
                            st.success("Comprovante armazenado com sucesso!")
                            st.rerun()
    st.subheader("Comprovantes armazenados")
    try:
        anexos = listar_anexos_ipb(emprestimo_id=emprestimo_id)
    except Exception as erro:
        st.error(f"Não foi possível consultar os comprovantes ({type(erro).__name__}). Execute o SQL primeiro.")
        return
    if not anexos:
        st.info("Nenhum comprovante anexado a este empréstimo.")
    for a in anexos:
        b = next((x for x in relacionados if x["id"] == a.get("patrimonio_id")), None)
        titulo = f"{a['nome_arquivo']} — {a['tipo']} — {b['codigo'] if b else 'Empréstimo completo'}"
        with st.expander(titulo):
            st.caption(f"Enviado em {a['criado_em']} • {a['tamanho_bytes']/1024:.0f} KB")
            if st.button("Carregar documento para baixar", key="abrir_" + a["id"]):
                try:
                    st.session_state["anexo_download_" + a["id"]] = requisicao_storage("GET", a["caminho"])
                except Exception as erro:
                    st.error(f"Não foi possível acessar o documento ({type(erro).__name__}).")
            conteudo = st.session_state.get("anexo_download_" + a["id"])
            if conteudo is not None:
                st.download_button("Baixar documento", data=conteudo,
                    file_name=a["nome_arquivo"], mime=a["mime_type"], key="baixar_" + a["id"])


def pagina_historico_patrimonio():
    st.header("Histórico por patrimônio")
    st.caption("Movimentações de empréstimo e devolução de cada bem")
    try:
        bens = listar_patrimonios()
        emprestimos = listar_emprestimos()
        pessoas = {p["id"]: p for p in listar_pessoas()}
    except Exception as erro:
        st.error(f"Não foi possível consultar os registros ({type(erro).__name__}).")
        return
    if not bens:
        st.info("Não existem patrimônios cadastrados.")
        return
    mapa = {b["id"]: b for b in bens}
    patrimonio_id = st.selectbox("Selecione o patrimônio", list(mapa),
        format_func=lambda i: f"{mapa[i]['codigo']} — {mapa[i]['descricao']}")
    bem = mapa[patrimonio_id]
    st.write(f"**Situação atual:** {bem.get('situacao') or '—'}")
    try:
        itens = (api_usuario(st.session_state["access_token"])
            .from_("itens_emprestimo")
            .select("emprestimo_id,estado_na_retirada,data_devolucao,estado_na_devolucao,responsavel_devolucao,observacoes")
            .eq("patrimonio_id", patrimonio_id).execute()).data or []
        anexos = listar_anexos_ipb(patrimonio_id=patrimonio_id)
        # Comprovantes de empréstimo completo também aparecem no histórico do bem.
        emprestimo_ids = {i["emprestimo_id"] for i in itens}
        for e_id in emprestimo_ids:
            gerais = listar_anexos_ipb(emprestimo_id=e_id)
            anexos.extend(a for a in gerais if a.get("patrimonio_id") is None)
    except Exception as erro:
        st.error(f"Falha ao consultar o histórico ({type(erro).__name__}).")
        return
    por_emprestimo = {e["id"]: e for e in emprestimos}
    linhas = []
    for item in itens:
        e = por_emprestimo.get(item["emprestimo_id"], {})
        linhas.append({
            "Empréstimo": e.get("numero", "—"),
            "Recebedor": pessoas.get(e.get("pessoa_id"), {}).get("nome", "—"),
            "Retirada": e.get("data_retirada", "—"),
            "Devolução": item.get("data_devolucao") or "Pendente",
            "Estado na retirada": item.get("estado_na_retirada") or "—",
            "Estado na devolução": item.get("estado_na_devolucao") or "—",
            "Responsável devolução": item.get("responsavel_devolucao") or "—",
        })
    st.dataframe(linhas, use_container_width=True, hide_index=True)
    st.caption(f"{len(linhas)} movimentação(ões) registrada(s)")
    st.subheader("Comprovantes relacionados")
    if anexos:
        vistos = set()
        for a in anexos:
            if a["id"] in vistos:
                continue
            vistos.add(a["id"])
            st.write(f"• {a['nome_arquivo']} ({a['tipo']}) — empréstimo {por_emprestimo.get(a['emprestimo_id'],{}).get('numero','—')}")
        st.caption("Para baixar os documentos, acesse a aba Documentos assinados.")
    else:
        st.info("Nenhum comprovante relacionado a este patrimônio.")



# =========================================================
# RELATÓRIOS PATRIMONIAIS — CONSULTA, PDF E EXCEL
# =========================================================
def relatorio_buscar_todos(tabela, campos, ordem="id"):
    registros = []
    pagina = 0
    while True:
        resposta = (api_usuario(st.session_state["access_token"])
                    .from_(tabela).select(campos).order(ordem)
                    .range(pagina * 500, pagina * 500 + 499).execute())
        lote = resposta.data or []
        registros.extend(lote)
        if len(lote) < 500:
            break
        pagina += 1
    return registros


def relatorio_pdf(titulo, colunas, linhas, resumo):
    from io import BytesIO
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle

    saida = BytesIO()
    documento = SimpleDocTemplate(saida, pagesize=landscape(A4),
        rightMargin=1.2*cm, leftMargin=1.2*cm, topMargin=1.3*cm, bottomMargin=1.3*cm)
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle(name="IPBRelatorio", parent=estilos["Title"],
        alignment=TA_CENTER, textColor=colors.HexColor("#075039"), fontSize=16))
    estilos.add(ParagraphStyle(name="IPBCelula", parent=estilos["BodyText"],
        fontSize=7, leading=9))
    def celula(valor):
        return Paragraph(escape(str(valor if valor is not None else "—")), estilos["IPBCelula"])
    elementos = [Paragraph("IGREJA PRESBITERIANA DO BRASIL — IPB CABO", estilos["IPBRelatorio"]),
        Paragraph(escape(titulo), estilos["Heading2"]),
        Paragraph(escape(resumo), estilos["Normal"]), Spacer(1, .4*cm)]
    if linhas:
        dados = [[celula(c) for c in colunas]]
        dados += [[celula(l.get(c, "—")) for c in colunas] for l in linhas]
        largura = landscape(A4)[0] - 2.4*cm
        tabela = LongTable(dados, colWidths=[largura/len(colunas)]*len(colunas), repeatRows=1)
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#dcece2")),
            ("GRID", (0,0), (-1,-1), .25, colors.HexColor("#bccfc2")),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f4f8f5")]),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        elementos.append(tabela)
    else:
        elementos.append(Paragraph("Nenhum registro encontrado.", estilos["Normal"]))
    def rodape(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(landscape(A4)[0] - 1.2*cm, .7*cm, f"Página {doc.page}")
    documento.build(elementos, onFirstPage=rodape, onLaterPages=rodape)
    return saida.getvalue()


def relatorio_excel(titulo, colunas, linhas, resumo):
    from io import BytesIO
    import xlsxwriter
    saida = BytesIO()
    workbook = xlsxwriter.Workbook(saida, {"in_memory": True})
    ws = workbook.add_worksheet("Relatório")
    cab = workbook.add_format({"bold": True, "bg_color": "#075039", "font_color": "white", "border": 1})
    titulo_fmt = workbook.add_format({"bold": True, "font_size": 16, "font_color": "#075039"})
    normal = workbook.add_format({"text_wrap": True, "valign": "top"})
    ws.write(0, 0, "IPB - CABO | " + titulo, titulo_fmt)
    ws.write(1, 0, resumo)
    for j, coluna in enumerate(colunas):
        ws.write(3, j, coluna, cab)
        ws.set_column(j, j, min(38, max(16, len(coluna)+5)))
    for i, linha in enumerate(linhas, 4):
        for j, coluna in enumerate(colunas):
            valor = linha.get(coluna)
            # Strings iniciadas por =, +, - ou @ são gravadas como texto, nunca fórmula.
            if valor is None:
                valor = ""
            if isinstance(valor, (int, float)) and not isinstance(valor, bool):
                ws.write_number(i, j, valor, normal)
            else:
                ws.write_string(i, j, str(valor), normal)
    if colunas:
        ws.autofilter(3, 0, max(4, len(linhas)+3), len(colunas)-1)
    ws.freeze_panes(4, 0)
    ws.set_landscape()
    ws.fit_to_pages(1, 0)
    workbook.close()
    return saida.getvalue()


def pagina_relatorios():
    st.header("Relatórios patrimoniais")
    st.caption("Inventário, movimentações, pendências e valores — IPB CABO")
    hoje = date.today()
    tipo = st.selectbox("Tipo de relatório", [
        "Inventário patrimonial", "Empréstimos ativos", "Empréstimos atrasados",
        "Histórico de empréstimos", "Histórico de devoluções", "Valores patrimoniais"
    ])
    try:
        bens = listar_patrimonios()
        categorias = {x["id"]: x["nome"] for x in listar_referencias("categorias")}
        locais = {x["id"]: x["nome"] for x in listar_referencias("localizacoes")}
        pessoas = {x["id"]: x["nome"] for x in relatorio_buscar_todos("pessoas", "id,nome", "nome")}
    except Exception as erro:
        LOG.warning("Falha nos dados de relatório: %s", type(erro).__name__)
        st.error("Não foi possível consultar os dados do relatório. Confira as permissões.")
        return
    fc, fl, fs = st.columns(3)
    with fc:
        categorias_opts = ["Todas"] + sorted(set(categorias.values()))
        categoria = st.selectbox("Categoria", categorias_opts)
    with fl:
        locais_opts = ["Todas"] + sorted(set(locais.values()))
        local = st.selectbox("Localização", locais_opts)
    with fs:
        situacao = st.selectbox("Situação", ["Todas", "disponivel", "emprestado", "manutencao"])
    bens_filtrados = [b for b in bens if
        (categoria == "Todas" or categorias.get(b.get("categoria_id")) == categoria) and
        (local == "Todas" or locais.get(b.get("localizacao_id")) == local) and
        (situacao == "Todas" or b.get("situacao") == situacao)]
    bens_ids = {b["id"] for b in bens_filtrados}
    colunas = []
    linhas = []
    periodo = ""
    if tipo in ("Inventário patrimonial", "Valores patrimoniais"):
        for b in bens_filtrados:
            linha = {"Código": b.get("codigo") or "", "Descrição": b.get("descricao") or "",
                "Categoria": categorias.get(b.get("categoria_id"), "Não informada"),
                "Localização": locais.get(b.get("localizacao_id"), "Não informada"),
                "Situação": b.get("situacao") or "", "Conservação": b.get("estado_conservacao") or "",
                "Valor (R$)": float(b.get("valor_aquisicao") or 0)}
            linhas.append(linha)
        colunas = ["Código", "Descrição", "Categoria", "Localização", "Situação", "Conservação", "Valor (R$)"]
        total = sum(x["Valor (R$)"] for x in linhas)
        c1, c2, c3 = st.columns(3)
        c1.metric("Bens", len(linhas))
        c2.metric("Com valor informado", sum(b.get("valor_aquisicao") is not None for b in bens_filtrados))
        c3.metric("Valor registrado (R$)", f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        if tipo == "Valores patrimoniais":
            st.caption("Soma dos valores de aquisição registrados; não é avaliação de mercado nem depreciação.")
    else:
        inicio, fim = None, None
        if tipo in ("Histórico de empréstimos", "Histórico de devoluções"):
            ci, cf = st.columns(2)
            with ci:
                inicio = st.date_input("Data inicial", value=date(hoje.year, 1, 1), format="DD/MM/YYYY")
            with cf:
                fim = st.date_input("Data final", value=hoje, format="DD/MM/YYYY")
            if inicio > fim:
                st.warning("A data inicial deve ser anterior ou igual à data final.")
                return
            periodo = f" | Período: {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}"
        try:
            emprestimos = relatorio_buscar_todos("emprestimos",
                "id,numero,pessoa_id,data_retirada,data_prevista_devolucao,status,finalidade,responsavel_entrega,responsavel_recebimento", "numero")
            itens = relatorio_buscar_todos("itens_emprestimo",
                "id,emprestimo_id,patrimonio_id,data_devolucao,estado_na_devolucao,responsavel_devolucao", "id")
        except Exception as erro:
            LOG.warning("Falha na consulta de movimentações: %s", type(erro).__name__)
            st.error("Não foi possível carregar as movimentações.")
            return
        bens_map = {b["id"]: b for b in bens}
        emprestimos_map = {e["id"]: e for e in emprestimos}
        for item in itens:
            if item.get("patrimonio_id") not in bens_ids:
                continue
            e = emprestimos_map.get(item["emprestimo_id"])
            if not e:
                continue
            retirada = e.get("data_retirada") or ""
            devolucao = item.get("data_devolucao") or ""
            prevista = e.get("data_prevista_devolucao") or ""
            if tipo == "Empréstimos ativos" and devolucao:
                continue
            if tipo == "Empréstimos atrasados" and (devolucao or not prevista or prevista >= hoje.isoformat()):
                continue
            if tipo == "Histórico de empréstimos" and not (inicio.isoformat() <= retirada <= fim.isoformat()):
                continue
            if tipo == "Histórico de devoluções" and not (devolucao and inicio.isoformat() <= devolucao <= fim.isoformat()):
                continue
            b = bens_map.get(item["patrimonio_id"], {})
            linhas.append({"Nº": e.get("numero"), "Código": b.get("codigo") or "",
                "Patrimônio": b.get("descricao") or "", "Recebedor": pessoas.get(e.get("pessoa_id"), "—"),
                "Retirada": retirada, "Previsão": prevista, "Devolução": devolucao or "Pendente",
                "Status": "Devolvido" if devolucao else ("Atrasado" if prevista and prevista < hoje.isoformat() else "Pendente"),
                "Responsável devolução": item.get("responsavel_devolucao") or ""})
        colunas = ["Nº", "Código", "Patrimônio", "Recebedor", "Retirada", "Previsão", "Devolução", "Status", "Responsável devolução"]
        st.metric("Movimentações encontradas", len(linhas))
        st.caption("Empréstimos são exibidos por bem. Pendências e atrasos consideram somente itens ainda não devolvidos.")
    st.caption(f"{len(linhas)} linha(s) no relatório")
    st.dataframe(linhas, use_container_width=True, hide_index=True)
    resumo = f"Emitido em {hoje:%d/%m/%Y} | Registros: {len(linhas)}{periodo} | Categoria: {categoria} | Local: {local} | Situação: {situacao}"
    try:
        pdf = relatorio_pdf(tipo, colunas, linhas, resumo)
        excel = relatorio_excel(tipo, colunas, linhas, resumo)
    except ImportError:
        st.error("Para exportar Excel, acrescente xlsxwriter ao requirements.txt. A biblioteca reportlab também é necessária para PDF.")
        return
    except Exception as erro:
        LOG.warning("Falha ao gerar relatórios: %s", type(erro).__name__)
        st.error("Não foi possível gerar os arquivos do relatório.")
        return
    cpdf, cexcel = st.columns(2)
    with cpdf:
        st.download_button("Baixar relatório em PDF", data=pdf, file_name="relatorio_ipb_cabo.pdf",
            mime="application/pdf", type="primary", use_container_width=True)
    with cexcel:
        st.download_button("Baixar relatório em Excel", data=excel, file_name="relatorio_ipb_cabo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)


# ==========================================
# ADMINISTRACAO DE USUARIOS
# ==========================================

def funcao_admin_ipb(acao, **campos):
    import json
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    url = st.secrets["SUPABASE_URL"].rstrip("/") + "/functions/v1/ipb-usuarios"
    payload = json.dumps({"acao": acao, **campos}).encode("utf-8")
    req = Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "apikey": st.secrets["SUPABASE_ANON_KEY"],
        "Authorization": "Bearer " + st.session_state["access_token"],
    })
    try:
        with urlopen(req, timeout=35) as r:
            return json.loads(r.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            msg = json.loads(exc.read().decode("utf-8")).get("erro", "Falha na operacao")
        except Exception:
            msg = "Falha na operacao"
        raise ValueError(msg) from None


def pagina_usuarios_ipb(papel):
    st.header("Administração de usuários")
    st.caption("Convites, permissões e controle de acesso ao sistema")
    if papel != "admin":
        st.error("Acesso exclusivo do administrador.")
        return
    if st.session_state.pop("usuarios_sucesso", None):
        st.success("Operação realizada com sucesso.")
    try:
        resposta = api_usuario(st.session_state["access_token"]).from_("perfis").select("id,nome_completo,papel,ativo").order("nome_completo").execute()
        perfis = resposta.data or []
    except Exception as exc:
        st.error("Não foi possível consultar os usuários: " + type(exc).__name__)
        return
    st.metric("Usuários cadastrados", len(perfis))
    st.dataframe([{"Nome": x.get("nome_completo") or "—", "Perfil": x.get("papel") or "—", "Situação": "Ativo" if x.get("ativo") else "Bloqueado", "ID": x["id"]} for x in perfis], use_container_width=True, hide_index=True)
    abas = st.tabs(["Convidar usuário", "Alterar permissões / bloquear"])
    with abas[0]:
        st.info("O usuário receberá um convite para configurar o acesso por e-mail. Configure o envio de e-mails do Supabase Auth para uso em produção.")
        with st.form("convite_usuario_ipb"):
            nome = st.text_input("Nome completo *")
            email = st.text_input("E-mail *")
            perfil_novo = st.selectbox("Perfil de acesso", ["consulta", "gestor", "admin"], format_func=lambda x: {"consulta":"Consulta", "gestor":"Gestor", "admin":"Administrador"}[x])
            enviar = st.form_submit_button("Enviar convite", type="primary", use_container_width=True)
        if enviar:
            if not nome.strip() or "@" not in email or not email.strip():
                st.error("Informe nome e e-mail válidos.")
            else:
                try:
                    funcao_admin_ipb("criar", nome=nome.strip(), email=email.strip().lower(), papel=perfil_novo)
                except Exception as exc:
                    st.error(str(exc))
                else:
                    st.success("Convite solicitado com sucesso. Confira o e-mail do destinatário.")
    with abas[1]:
        outros = [p for p in perfis if p["id"] != st.session_state["user_id"]]
        if not outros:
            st.info("Ainda não há outros usuários para administrar.")
        else:
            mapa = {p["id"]: p for p in outros}
            selecionado = st.selectbox("Usuário", list(mapa), format_func=lambda i: f"{mapa[i].get('nome_completo') or 'Sem nome'} — {mapa[i].get('papel')}")
            atual = mapa[selecionado]
            papeis = ["consulta", "gestor", "admin"]
            with st.form("editar_usuario_ipb_" + selecionado):
                papel_editado = st.selectbox("Perfil", papeis, index=papeis.index(atual["papel"]) if atual.get("papel") in papeis else 0)
                ativo = st.checkbox("Usuário ativo", value=bool(atual.get("ativo")))
                salvar = st.form_submit_button("Salvar alterações", type="primary", use_container_width=True)
            if salvar:
                try:
                    funcao_admin_ipb("alterar", usuario_id=selecionado, papel=papel_editado, ativo=ativo)
                except Exception as exc:
                    st.error(str(exc))
                else:
                    st.session_state["usuarios_sucesso"] = True
                    st.rerun()
    st.caption("Por segurança, sua própria conta não pode ser bloqueada ou rebaixada nesta tela. Alterações de acesso entram em vigor nas próximas consultas autorizadas pelo banco.")

def painel_principal(nome):
    """Visão gerencial baseada nos registros acessíveis ao usuário autenticado."""
    from collections import Counter
    from datetime import datetime
    from html import escape

    st.markdown("""
    <style>
      .ipb-dashboard-intro {background:linear-gradient(115deg,#0c6447,#0b4b38);
        border:1px solid #408e70;border-radius:18px;padding:21px 24px;
        margin:2px 0 19px;box-shadow:0 12px 30px #001f142c}
      .ipb-dashboard-intro .eyebrow {color:#aee2c7;font-size:.78rem;
        letter-spacing:.12em;font-weight:750;text-transform:uppercase}
      .ipb-dashboard-intro h2 {color:#fff!important;font-size:1.6rem;
        margin:6px 0 5px;font-weight:750}
      .ipb-dashboard-intro p {color:#d5ede0!important;margin:0;font-size:.94rem}
      .ipb-kpi {background:linear-gradient(155deg,#ffffff,#eff7f1);color:#143f30;
        border:1px solid #b9d6c5;border-radius:17px;padding:19px 17px;
        min-height:137px;box-shadow:0 7px 22px #001d151e;margin-bottom:9px}
      .ipb-kpi .ipb-kpi-label {font-size:.83rem;color:#446c57;font-weight:700}
      .ipb-kpi .ipb-kpi-value {font-size:2.2rem;line-height:1.25;
        color:#0a5038;font-weight:800;margin-top:11px}
      .ipb-kpi .ipb-kpi-foot {font-size:.76rem;color:#527561;margin-top:4px}
      .ipb-section-label {font-size:1.13rem;font-weight:750;color:#e6f6eb;
        margin:19px 0 11px}
      .ipb-note {background:#0d513b;border:1px solid #4b8d6e;
        border-radius:13px;padding:13px 17px;color:#e8f5ed;margin:8px 0}
      @media(max-width:700px){.ipb-dashboard-intro{padding:16px}
        .ipb-dashboard-intro h2{font-size:1.3rem}.ipb-kpi{min-height:110px}}
    </style>
    """, unsafe_allow_html=True)
    st.markdown(
        '<div class="ipb-dashboard-intro"><div class="eyebrow">Visão geral do patrimônio</div>'
        f'<h2>Bem-vindo(a), {escape(str(nome))}</h2>'
        '<p>Acompanhe os bens da igreja e os empréstimos em um só lugar.</p></div>',
        unsafe_allow_html=True,
    )
    try:
        registros = listar_patrimonios()
    except Exception as erro:
        LOG.warning("Falha ao carregar indicadores: %s", type(erro).__name__)
        st.warning("Não foi possível carregar os indicadores do Supabase.")
        return

    situacoes = Counter(str(r.get("situacao") or "nao_informado").lower() for r in registros)
    total = len(registros)
    disponiveis = situacoes.get("disponivel", 0)
    emprestados = situacoes.get("emprestado", 0)
    manutencao = situacoes.get("manutencao", 0)
    indicadores = [
        ("▦", "Patrimônios cadastrados", total, "Total de bens registrados"),
        ("✓", "Disponíveis", disponiveis, "Prontos para utilização"),
        ("↗", "Emprestados", emprestados, "Bens fora da disponibilidade"),
        ("⚒", "Em manutenção", manutencao, "Bens que exigem atenção"),
    ]
    cols = st.columns(4)
    for col, (icone, titulo, valor, rodape) in zip(cols, indicadores):
        with col:
            st.markdown(
                f'<div class="ipb-kpi"><div class="ipb-kpi-label">{icone} &nbsp;{titulo}</div>'
                f'<div class="ipb-kpi-value">{valor:,}</div>'
                f'<div class="ipb-kpi-foot">{rodape}</div></div>',
                unsafe_allow_html=True,
            )

    try:
        emprestimos = listar_emprestimos()
    except Exception as erro:
        LOG.warning("Falha ao carregar resumo de empréstimos: %s", type(erro).__name__)
        st.info("O resumo de empréstimos está temporariamente indisponível.")
    else:
        hoje = date.today()
        atrasados = []
        for emp in emprestimos:
            status = str(emp.get("status") or "").lower()
            # Não tratar empréstimos devolvidos ou cancelados como pendentes.
            if status in ("devolvido", "concluido", "cancelado", "finalizado"):
                continue
            prevista = str(emp.get("data_prevista_devolucao") or "")[:10]
            try:
                prazo = date.fromisoformat(prevista)
            except ValueError:
                continue
            if prazo < hoje:
                atrasados.append(emp)
        # Valores calculados a partir dos bens cadastrados no Supabase.
        def valor_do_bem(registro):
            try:
                return Decimal(str(registro.get("valor_aquisicao") or 0))
            except (InvalidOperation, ValueError, TypeError):
                return Decimal("0")

        def reais(valor):
            return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        valor_total = sum((valor_do_bem(r) for r in registros), Decimal("0"))
        valor_emprestado = sum(
            (valor_do_bem(r) for r in registros
             if str(r.get("situacao") or "").strip().lower() == "emprestado"),
            Decimal("0"),
        )
        indicadores_emprestimos = [
            ("Valor total do patrimônio", reais(valor_total), "Soma dos valores de aquisição informados"),
            ("Valor total dos bens emprestados", reais(valor_emprestado), "Soma dos valores dos patrimônios emprestados"),
        ]
        for coluna, (titulo, valor, rodape) in zip(st.columns(2), indicadores_emprestimos):
            with coluna:
                st.markdown(
                    f'<div class="ipb-kpi"><div class="ipb-kpi-label">{escape(titulo)}</div>'
                    f'<div class="ipb-kpi-value" style="font-size:clamp(1.35rem,2.5vw,2.1rem);overflow-wrap:anywhere">{escape(valor)}</div>'
                    f'<div class="ipb-kpi-foot">{escape(rodape)}</div></div>',
                    unsafe_allow_html=True,
                )
        if atrasados:
            st.warning(f"Há {len(atrasados)} empréstimo(s) com prazo vencido. Consulte a aba Devoluções para conferir os registros.")
            import pandas as pd
            st.dataframe(pd.DataFrame([
                {"Recibo": e.get("numero", "—"),
                 "Previsão de devolução": str(e.get("data_prevista_devolucao") or "")[:10],
                 "Status": e.get("status") or "Não informado"}
                for e in atrasados[:10]
            ]), hide_index=True, use_container_width=True)
        else:
            st.markdown('<div class="ipb-note">✓ Nenhum empréstimo com prazo vencido identificado nos registros consultados.</div>', unsafe_allow_html=True)
        st.caption("Resumo de empréstimos limitado aos 500 registros mais recentes disponíveis na consulta atual.")
    st.caption("Dados consultados no Supabase. Atualize a página para consultar novamente.")


if not st.session_state.get("access_token"):
    tela_login()
if not validar_sessao():
    limpar_sessao()
    st.warning("Sua sessão expirou. Entre novamente.")
    tela_login()

perfil = st.session_state["profile"]
papel = perfil.get("papel") or "consulta"
nome = perfil.get("nome_completo") or "Usuário"

with st.sidebar:
    # Sarça centralizada no painel lateral, usando a imagem original.
    col_esq, col_logo, col_dir = st.columns([1, 1.5, 1])
    with col_logo:
        mostrar_logo(105)
    st.markdown('<h2 style="text-align:center; color:#ffffff; font-size:1.65rem; margin:0.35rem 0 0.1rem;">IPB - CABO</h2>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:#b9dccc; margin:0 0 1rem;">Gestão Patrimonial</p>', unsafe_allow_html=True)
    st.divider()
    st.write("**Usuário:**", nome)
    st.caption("Perfil: " + papel.upper())
    st.divider()
    st.divider()
    if st.button("Sair do sistema", use_container_width=True):
        limpar_sessao()
        st.rerun()

# Usa a mesma imagem da sarça já utilizada no menu lateral.
# A imagem é embutida no cabeçalho para manter a posição à esquerda do título.
logo_html = ""
if LOGO_PATH.is_file():
    try:
        logo_base64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
        extensao_logo = LOGO_PATH.suffix.lower()
        mime_logo = "image/png" if extensao_logo == ".png" else "image/jpeg"
        logo_html = (
            f'<img class="ipb-banner-logo" '
            f'src="data:{mime_logo};base64,{logo_base64}" '
            f'alt="Sarça da Igreja Presbiteriana" />'
        )
    except OSError:
        pass
st.markdown(
    '<div class="ipb-banner">'
    + logo_html
    + '<div class="ipb-banner-copy">'
    + '<h1 class="ipb-igreja-nome">Primeira Igreja Presbiteriana do Cabo</h1>'
    + '<p class="ipb-sistema-nome">Sistema de Gestão Patrimonial</p>'
    + '</div></div>',
    unsafe_allow_html=True,
)


# Navegação horizontal: mantém os mesmos módulos e permissões do menu original.
paginas = ["Painel principal", "Patrimônios", "Empréstimos", "Devoluções", "Documentos assinados", "Histórico por patrimônio", "Relatórios"]
if papel == "admin":
    paginas.append("Usuários")
icones_menu = {
    "Painel principal": "▦",
    "Patrimônios": "▣",
    "Empréstimos": "↗",
    "Devoluções": "↙",
    "Documentos assinados": "▤",
    "Histórico por patrimônio": "◷",
    "Relatórios": "▥",
    "Usuários": "♙",
}

pagina = st.radio(
    "Navegação principal", paginas,
    horizontal=True,
    label_visibility="collapsed",
    format_func=lambda item: f"{icones_menu.get(item, '•')}  {item}",
    key="navegacao_ipb",
)

if pagina == "Painel principal":
    painel_principal(nome)
elif pagina == "Patrimônios":
    pagina_patrimonios(papel)
elif pagina == "Empréstimos":
    pagina_emprestimos(papel, nome)
elif pagina == "Devoluções":
    pagina_devolucoes(papel, nome)
elif pagina == "Documentos assinados":
    pagina_documentos(papel)
elif pagina == "Histórico por patrimônio":
    pagina_historico_patrimonio()
elif pagina == "Relatórios":
    pagina_relatorios()
elif pagina == "Usuários":
    if papel != "admin":
        st.error("Acesso restrito ao administrador.")
        st.stop()
    pagina_usuarios_ipb(papel)
else:
    st.header(pagina)
    st.info("Módulo em desenvolvimento. Nenhum dado será alterado nesta tela.")
