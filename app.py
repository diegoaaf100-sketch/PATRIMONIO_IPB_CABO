import streamlit as st
from pathlib import Path
from PIL import Image
from supabase import create_client
from postgrest import SyncPostgrestClient

st.set_page_config(
    page_title="Sistema de Gestão Patrimonial IPB - CABO",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets" / "logo_ipb.png"

st.markdown("""
<style>
:root { --verde:#073f30; --verde2:#0b503a; --verde3:#146348; --claro:#e7f3ec; --branco:#ffffff; }
html, body, [data-testid="stAppViewContainer"], .stApp { background:var(--verde) !important; color:var(--branco) !important; }
[data-testid="stHeader"] { background:rgba(7,63,48,.94) !important; }
[data-testid="stMainBlockContainer"] { padding-top:2.1rem; padding-bottom:3rem; }
[data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3,
[data-testid="stMain"] p, [data-testid="stMain"] label,
[data-testid="stMain"] [data-testid="stCaptionContainer"] { color:#fff !important; }
[data-testid="stMain"] [data-testid="stCaptionContainer"] { opacity:.82; }
[data-testid="stSidebar"] { background:#052e23 !important; border-right:1px solid #21634b; }
[data-testid="stSidebar"] * { color:#fff !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding:10px 12px; border-radius:10px; transition:background .2s; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:#18553f; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background:#176448 !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p { font-weight:600; }
[data-testid="stSidebar"] [data-testid="stButton"] button { background:#fff !important; color:#073f30 !important; border:1px solid #fff !important; border-radius:10px; font-weight:700; }
[data-testid="stSidebar"] [data-testid="stButton"] button p { color:#073f30 !important; }
[data-testid="stSidebar"] [data-testid="stButton"] button:hover { background:#d9eee2 !important; }
[data-testid="stForm"] { background:#fff !important; border:1px solid #d7e8dc !important; border-radius:18px !important; padding:25px !important; box-shadow:0 15px 34px rgba(0,0,0,.17); }
[data-testid="stForm"] label, [data-testid="stForm"] p { color:#143e2e !important; }
[data-testid="stTextInput"] input { border-radius:9px !important; background:#f9fcfa !important; color:#183c2e !important; border:1px solid #c9dacf !important; }
[data-testid="stTextInput"] input::placeholder { color:#73847a !important; }
[data-testid="stFormSubmitButton"] button,
[data-testid="stFormSubmitButton"] button[kind="primary"],
.stButton button[kind="primary"] { background:#075c3e !important; border:1px solid #075c3e !important; color:#fff !important; border-radius:10px !important; font-weight:700 !important; min-height:43px; }
[data-testid="stFormSubmitButton"] button p, .stButton button[kind="primary"] p { color:#fff !important; }
[data-testid="stFormSubmitButton"] button:hover, .stButton button[kind="primary"]:hover { background:#03482f !important; border-color:#03482f !important; }
[data-testid="stMetric"] { background:#fff !important; border:1px solid #d8e8dd !important; border-radius:15px !important; padding:18px !important; min-height:140px; box-shadow:0 5px 16px rgba(0,0,0,.12); }
[data-testid="stMetric"] label, [data-testid="stMetric"] label p { color:#315c46 !important; font-weight:600 !important; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * { color:#073f30 !important; }
[data-testid="stAlert"] { border-radius:12px !important; }
[data-testid="stMain"] hr { border-color:#3d7660 !important; }
.ipb-hero { border:1px solid #36785c; background:linear-gradient(115deg,#0b513b,#073f30); padding:26px 30px; border-radius:20px; margin:5px 0 24px; box-shadow:0 12px 26px rgba(0,0,0,.12); }
.ipb-hero h1 { color:#fff !important; margin:0 0 9px; font-size:clamp(1.5rem,3vw,2.5rem); line-height:1.2; }
.ipb-hero p { color:#d7e9dd !important; margin:0; font-size:1rem; }
.ipb-section { color:#fff; font-size:1.65rem; font-weight:700; margin:0 0 14px; }
.ipb-note { background:#15533f; border:1px solid #2e7658; color:#fff; border-radius:12px; padding:15px 18px; margin:8px 0 16px; }
.ipb-note strong { color:#fff; }
.ipb-subnote { color:#cfe6d7 !important; font-size:.86rem; margin-top:10px; }
.ipb-login-brand { text-align:center; }
.ipb-login-brand h1 { color:#fff !important; font-size:clamp(1.65rem,3vw,2.2rem); line-height:1.2; margin:8px 0 4px; }
.ipb-login-brand .ipb-accent { color:#bde7cf !important; font-weight:800; letter-spacing:3px; margin:12px 0; }
.ipb-login-brand .ipb-caption { color:#d2e8da !important; margin-bottom:22px; }
@media (max-width:768px) { [data-testid="stMainBlockContainer"] { padding-top:1rem; } [data-testid="stForm"] { padding:15px !important; } .ipb-hero { padding:19px; } [data-testid="stMetric"] { min-height:110px; } }
</style>
""", unsafe_allow_html=True)


def mostrar_logo(largura=145):
    caminhos = [LOGO_PATH, Path.cwd() / "assets" / "logo_ipb.png"]
    for caminho in caminhos:
        if caminho.is_file():
            try:
                with Image.open(caminho) as imagem:
                    imagem.load()
                    st.image(imagem.copy(), width=largura)
                return
            except Exception:
                st.warning("Não foi possível abrir a imagem da logo.")
                return
    st.warning("Logo não encontrada em assets/logo_ipb.png.")


def cliente():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])


def consultar_perfil(token, user_id):
    api = SyncPostgrestClient(
        st.secrets["SUPABASE_URL"].rstrip("/") + "/rest/v1",
        headers={
            "apikey": st.secrets["SUPABASE_ANON_KEY"],
            "Authorization": "Bearer " + token,
        },
    )
    resposta = (
        api.from_("perfis")
        .select("id,nome_completo,papel,ativo")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    return resposta.data[0] if resposta.data else None


def limpar_sessao():
    for chave in ("access_token", "refresh_token", "user_id", "profile"):
        st.session_state.pop(chave, None)


def sair():
    limpar_sessao()
    st.rerun()


def autenticar(email, senha):
    resposta = cliente().auth.sign_in_with_password({"email": email, "password": senha})
    if not resposta.session or not resposta.user:
        raise ValueError("Falha de autenticação")
    perfil = consultar_perfil(resposta.session.access_token, resposta.user.id)
    if not perfil or not perfil.get("ativo"):
        raise PermissionError("Conta não autorizada")
    st.session_state.update({
        "access_token": resposta.session.access_token,
        "refresh_token": resposta.session.refresh_token,
        "user_id": resposta.user.id,
        "profile": perfil,
    })


def validar_sessao():
    if not st.session_state.get("refresh_token"):
        return False
    try:
        resposta = cliente().auth.refresh_session(st.session_state["refresh_token"])
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
        })
        return True
    except Exception:
        return False


def tela_login():
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    _, centro, _ = st.columns([1, 1.35, 1])
    with centro:
        _, coluna_logo, _ = st.columns([1, 1, 1])
        with coluna_logo:
            mostrar_logo(145)
        st.markdown("""
        <div class="ipb-login-brand">
          <h1>Sistema de Gestão<br>Patrimonial</h1>
          <p class="ipb-accent">IPB - CABO</p>
          <p class="ipb-caption">Acesso restrito a usuários autorizados</p>
        </div>
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
                except PermissionError:
                    st.error("Seu usuário não possui um perfil ativo autorizado.")
                except Exception:
                    st.error("Não foi possível entrar. Verifique as credenciais ou a conexão com o Supabase.")
    st.stop()


if not st.session_state.get("access_token"):
    tela_login()
if not validar_sessao():
    limpar_sessao()
    st.rerun()

perfil = st.session_state["profile"]
papel = perfil["papel"]
with st.sidebar:
    mostrar_logo(105)
    st.header("IPB - CABO")
    st.caption("Gestão Patrimonial")
    st.divider()
    st.write("**Usuário:**", perfil.get("nome_completo") or "Usuário")
    st.caption("Perfil: " + str(papel).upper())
    st.divider()
    paginas = ["Painel principal", "Patrimônios", "Empréstimos", "Devoluções", "Relatórios"]
    if papel == "admin":
        paginas.append("Usuários")
    pagina = st.radio("Navegação", paginas, label_visibility="collapsed")
    st.divider()
    if st.button("Sair do sistema", use_container_width=True):
        sair()

st.markdown("""
<div class="ipb-hero">
  <h1>Sistema de Gestão Patrimonial IPB - CABO</h1>
  <p>Controle e administração dos bens patrimoniais</p>
</div>
""", unsafe_allow_html=True)

if pagina == "Painel principal":
    st.markdown('<div class="ipb-section">Painel principal</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ipb-note">Bem-vindo(a), <strong>'
        + __import__("html").escape(str(perfil.get("nome_completo") or "Usuário"))
        + '</strong>! Seu acesso foi validado pelo Supabase.</div>',
        unsafe_allow_html=True,
    )
    colunas = st.columns(4)
    for coluna, titulo in zip(colunas, ["Patrimônios", "Disponíveis", "Emprestados", "Em manutenção"]):
        with coluna:
            st.metric(titulo, "—")
    st.markdown(
        '<p class="ipb-subnote">Os indicadores ainda não consultam o banco de dados. '
        'Os módulos de gestão estão em desenvolvimento.</p>',
        unsafe_allow_html=True,
    )
elif pagina == "Usuários":
    if papel != "admin":
        st.error("Acesso restrito ao administrador.")
        st.stop()
    st.markdown('<div class="ipb-section">Administração de usuários</div>', unsafe_allow_html=True)
    st.markdown('<div class="ipb-note">Módulo em desenvolvimento. Usuários ainda não podem ser criados nesta tela.</div>', unsafe_allow_html=True)
else:
    import html
    st.markdown('<div class="ipb-section">' + html.escape(pagina) + '</div>', unsafe_allow_html=True)
    st.markdown('<div class="ipb-note">Módulo em desenvolvimento. Nenhum dado será alterado nesta tela.</div>', unsafe_allow_html=True)
