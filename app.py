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

/* CORREÇÃO REFORÇADA: dropdowns do Streamlit/BaseWeb, inclusive portal fora do formulário.
   A cor permanece igual sem hover, no foco e na opção selecionada. */
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] [data-baseweb="menu"],
div[data-baseweb="popover"] [role="listbox"],
ul[role="listbox"],
ul[data-baseweb="menu"],
div[data-baseweb="menu"] {
  background: #103f30 !important;
  background-color: #103f30 !important;
  color: #ffffff !important;
}
div[data-baseweb="popover"] li,
div[data-baseweb="popover"] [role="option"],
ul[role="listbox"] li,
ul[role="listbox"] [role="option"],
[data-baseweb="menu"] li,
[data-baseweb="menu"] [role="option"],
li[role="option"] {
  background: #103f30 !important;
  background-color: #103f30 !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}
div[data-baseweb="popover"] li *,
div[data-baseweb="popover"] [role="option"] *,
ul[role="listbox"] li *,
ul[role="listbox"] [role="option"] *,
[data-baseweb="menu"] li *,
[data-baseweb="menu"] [role="option"] *,
li[role="option"] * {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}
div[data-baseweb="popover"] li:hover,
div[data-baseweb="popover"] [role="option"]:hover,
ul[role="listbox"] li:hover,
ul[role="listbox"] [role="option"]:hover,
[data-baseweb="menu"] li:hover,
[data-baseweb="menu"] [role="option"]:hover,
li[role="option"]:hover,
li[role="option"][aria-selected="true"] {
  background: #187855 !important;
  background-color: #187855 !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  background: #164d3d !important;
  color: #ffffff !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] *,
[data-testid="stMultiSelect"] [data-baseweb="select"] * {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}


/* Login: restaura o cartão verde, sem alterar formulários internos. */
[data-testid="stForm"]:has(input[placeholder="Digite seu e-mail"]) {
  background: #0b503c !important;
  border: 1px solid #347b61 !important;
  box-shadow: 0 12px 30px #001e1433 !important;
}
[data-testid="stForm"]:has(input[placeholder="Digite seu e-mail"]) label,
[data-testid="stForm"]:has(input[placeholder="Digite seu e-mail"]) label *,
[data-testid="stForm"]:has(input[placeholder="Digite seu e-mail"]) [data-testid="stWidgetLabel"] *,
[data-testid="stForm"]:has(input[placeholder="Digite seu e-mail"]) p {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

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
    # Foto da fachada exibida apenas na tela de autenticação.
    # Incorporada no código para não depender de arquivos adicionais no GitHub.
    st.markdown("""<style>
    /* Foto original preservada no centro; laterais com continuação suave da própria foto. */
    [data-testid="stAppViewContainer"] {
      position: relative !important;
      isolation: isolate !important;
      background-color: #557e7c !important;
    }
    [data-testid="stAppViewContainer"]::before {
      content: "";
      position: fixed;
      inset: -45px;
      background-image: linear-gradient(rgba(10,54,48,.24), rgba(10,54,48,.24)), url("data:image/jpeg;base64,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");
      background-size: cover;
      background-position: center;
      background-repeat: no-repeat;
      filter: blur(36px) saturate(.75) brightness(.82);
      transform: scale(1.05);
      z-index: -2;
      pointer-events: none;
    }
    [data-testid="stAppViewContainer"]::after {
      content: "";
      position: fixed;
      inset: 0;
      background-image: linear-gradient(rgba(2,43,31,.46), rgba(2,43,31,.46)), url("data:image/jpeg;base64,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");
      background-size: 100% 100%, auto 100%;
      background-position: center;
      background-repeat: no-repeat;
      z-index: -1;
      pointer-events: none;
    }
    [data-testid="stHeader"] {background: transparent !important;}
    [data-testid="stForm"]:has(input[placeholder="Digite seu e-mail"]) {
      background: rgba(5,62,44,.94) !important;
      border: 1px solid rgba(255,255,255,.52) !important;
      box-shadow: 0 12px 32px rgba(0,0,0,.35) !important;
    }
    @media(max-width:768px) {
      [data-testid="stAppViewContainer"]::after { background-size: 100% 100%, contain !important; }
    }
    </style>""", unsafe_allow_html=True)
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
            .select("id,codigo,descricao,categoria_id,localizacao_id,marca,modelo,numero_serie,data_aquisicao,valor_aquisicao,estado_conservacao,situacao,subgrupo,observacoes,foto_caminho,nota_fiscal_caminho,baixado_em,motivo_baixa,excluido_em,motivo_exclusao,criado_em,atualizado_em")
            .is_("excluido_em", "null")
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
    abas = ["Consultar patrimônios"] + (["Cadastrar patrimônio", "Editar patrimônio"] if pode_gerenciar else []) + (["Dar baixa", "Excluir patrimônio"] if papel == "admin" else [])
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
                "Situação": "Baixado" if r.get("baixado_em") else (r.get("situacao") or "—"),
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
    if aba == "Dar baixa" and papel == "admin":
        st.subheader("Dar baixa no patrimônio")
        st.info("A baixa retira o bem do patrimônio ativo, sem apagar documentos e histórico. Apenas o administrador pode realizar esta operação.")
        candidatos = [r for r in registros if not r.get("baixado_em")]
        if not candidatos:
            st.info("Não há bens ativos disponíveis para baixa.")
        else:
            mapa = {r["id"]: r for r in candidatos}
            id_baixa = st.selectbox("Bem para baixa", list(mapa),
                format_func=lambda i: f"{mapa[i].get('codigo', '')} — {mapa[i].get('descricao', '')}", key="id_baixa")
            motivo = st.selectbox("Motivo da baixa", ["Inutilização", "Doação", "Venda", "Extravio", "Outro"], key="motivo_baixa_tipo")
            detalhes = st.text_area("Justificativa / observações", key="motivo_baixa_detalhes")
            confirmar = st.checkbox("Confirmo a baixa deste patrimônio.", key="confirma_baixa")
            if st.button("Confirmar baixa", disabled=not confirmar, key="executar_baixa"):
                try:
                    api = api_usuario(st.session_state["access_token"])
                    ativos = (api.from_("itens_emprestimo").select("emprestimo_id")
                        .eq("patrimonio_id", id_baixa).execute()).data or []
                    if mapa[id_baixa].get("situacao") == "emprestado":
                        st.error("Registre a devolução antes de dar baixa neste patrimônio.")
                    else:
                        from datetime import datetime, timezone
                        resposta = (api.from_("patrimonios").update({
                            "baixado_em": datetime.now(timezone.utc).isoformat(),
                            "motivo_baixa": motivo + (" — " + detalhes.strip() if detalhes.strip() else "")
                        }).eq("id", id_baixa).select("id").execute())
                        if resposta.data:
                            st.session_state["mensagem_patrimonio"] = "Baixa registrada. O histórico do patrimônio foi preservado."
                            st.session_state["patrimonio_aba_pendente"] = "Consultar patrimônios"
                            st.rerun()
                        else:
                            st.error("Baixa não confirmada. Verifique a política RLS do Supabase.")
                except Exception as erro:
                    LOG.warning("Falha ao dar baixa: %s", type(erro).__name__)
                    st.error(f"Não foi possível registrar a baixa ({type(erro).__name__}).")
    if aba == "Excluir patrimônio" and papel == "admin":
        st.subheader("Exclusão administrativa de patrimônio")
        st.warning("A exclusão administrativa retira o bem das consultas e dos indicadores, mas mantém os registros vinculados para auditoria. Apenas o administrador pode executar esta ação.")
        if not registros:
            st.info("Não há patrimônios cadastrados para excluir.")
        else:
            mapa = {r["id"]: r for r in registros}
            id_exclusao = st.selectbox("Patrimônio a excluir", list(mapa),
                format_func=lambda i: f"{mapa[i].get('codigo', '')} — {mapa[i].get('descricao', '')}", key="patrimonio_excluir_id")
            bem = mapa[id_exclusao]
            st.write(f"**Código:** {bem.get('codigo') or '—'}")
            st.write(f"**Descrição:** {bem.get('descricao') or '—'}")
            justificativa = st.text_area("Motivo da exclusão *", key="motivo_exclusao_admin")
            confirmar = st.checkbox("Confirmo a exclusão administrativa deste bem.", key=f"confirma_exclusao_{id_exclusao}")
            if st.button("Excluir patrimônio", type="primary", disabled=not (confirmar and justificativa.strip()), key="executar_exclusao_patrimonio"):
                try:
                    from datetime import datetime, timezone
                    cliente = api_usuario(st.session_state["access_token"])
                    resposta = (cliente.from_("patrimonios").update({
                        "excluido_em": datetime.now(timezone.utc).isoformat(),
                        "motivo_exclusao": justificativa.strip()
                    }).eq("id", id_exclusao).select("id").execute())
                    if resposta.data:
                        st.session_state["mensagem_patrimonio"] = "Patrimônio excluído das consultas ativas. Histórico e documentos preservados."
                        st.session_state["patrimonio_aba_pendente"] = "Consultar patrimônios"
                        st.rerun()
                    else:
                        st.error("Exclusão não confirmada. Verifique as permissões RLS.")
                except Exception as erro:
                    LOG.warning("Falha na exclusão administrativa: %s", type(erro).__name__)
                    st.error(f"Não foi possível excluir ({type(erro).__name__}).")
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
        disponiveis = [b for b in bens if b.get("situacao") == "disponivel" and not b.get("baixado_em")]
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
