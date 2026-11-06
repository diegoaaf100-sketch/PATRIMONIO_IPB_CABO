import streamlit as st
from pathlib import Path
from PIL import Image
from supabase import create_client
from postgrest import SyncPostgrestClient

st.set_page_config(page_title="Sistema de Gestão Patrimonial IPB - CABO", page_icon="🌿", layout="wide", initial_sidebar_state="collapsed")
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets" / "logo_ipb.png"

st.markdown("""
<style>
.stApp { background: #f4f7f5; }
h1, h2, h3 { color: #123f30 !important; }
[data-testid="stSidebar"] { background: #123f30; }
[data-testid="stSidebar"] * { color: #fff !important; }
[data-testid="stForm"] { background: #fff; border: 1px solid #dbe7df; border-radius: 16px; padding: 22px; box-shadow: 0 10px 28px rgba(10,45,28,.07); }
[data-testid="stFormSubmitButton"] button,
[data-testid="stFormSubmitButton"] button[kind="primary"],
[data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primary"],
.stButton button[kind="primary"] {
  background: #006341 !important; background-color: #006341 !important;
  border: 1px solid #006341 !important; color: #fff !important;
  border-radius: 10px !important; font-weight: 650 !important;
}
[data-testid="stFormSubmitButton"] button:hover,
[data-testid="stFormSubmitButton"] button:focus,
.stButton button[kind="primary"]:hover {
  background: #004d32 !important; background-color: #004d32 !important;
  border-color: #004d32 !important; color: #fff !important;
}
[data-testid="stFormSubmitButton"] button p { color: #fff !important; }
[data-testid="stTextInput"] input { border-radius: 9px; }
[data-testid="stMetric"] { background: #fff; border: 1px solid #dbe7df; border-radius: 12px; padding: 15px; }
@media (max-width: 768px) { [data-testid="stForm"] { padding: 12px; } }
</style>
""", unsafe_allow_html=True)


def mostrar_logo(largura=145):
    if not LOGO_PATH.is_file():
        st.warning("Logo não encontrada: envie assets/logo_ipb.png para o GitHub.")
        return
    try:
        with Image.open(LOGO_PATH) as img:
            img.load()
            st.image(img.copy(), width=largura)
    except (OSError, ValueError) as exc:
        st.warning("O arquivo assets/logo_ipb.png não é uma imagem válida. Substitua pelo PNG fornecido.")


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
    resposta = api.from_("perfis").select("id,nome_completo,papel,ativo").eq("id", user_id).limit(1).execute()
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
        <h1 style="text-align:center;font-size:clamp(1.65rem,3vw,2.2rem);margin:8px 0 4px;">
          Sistema de Gestão<br>Patrimonial
        </h1>
        <p style="text-align:center;color:#006341;font-weight:750;letter-spacing:3px;margin:12px 0;">IPB - CABO</p>
        <p style="text-align:center;color:#66756d;margin-bottom:22px;">Acesso restrito a usuários autorizados</p>
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
                except Exception:
                    st.error("Não foi possível entrar. Confira suas credenciais e se a conta está ativa.")
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
    st.write("**Usuário:**", perfil["nome_completo"])
    st.caption("Perfil: " + papel.upper())
    st.divider()
    paginas = ["Painel principal", "Patrimônios", "Empréstimos", "Devoluções", "Relatórios"]
    if papel == "admin":
        paginas.append("Usuários")
    pagina = st.radio("Navegação", paginas, label_visibility="collapsed")
    st.divider()
    if st.button("Sair do sistema", use_container_width=True):
        sair()

st.title("Sistema de Gestão Patrimonial IPB - CABO")
st.caption("Controle e administração dos bens patrimoniais")
st.divider()

if pagina == "Painel principal":
    st.header("Painel principal")
    st.success(f"Bem-vindo(a), {perfil['nome_completo']}!")
    st.info("Login validado pelo Supabase. Os módulos de gestão ainda estão em desenvolvimento.")
    colunas = st.columns(4)
    for coluna, titulo in zip(colunas, ["Patrimônios", "Disponíveis", "Emprestados", "Em manutenção"]):
        with coluna:
            st.metric(titulo, "—")
    st.caption("Indicadores demonstrativos: ainda não consultam o banco de dados.")
elif pagina == "Usuários":
    if papel != "admin":
        st.error("Acesso restrito ao administrador.")
        st.stop()
    st.header("Administração de usuários")
    st.info("Módulo em desenvolvimento. Usuários ainda não podem ser criados nesta tela.")
else:
    st.header(pagina)
    st.info("Módulo em desenvolvimento. Nenhum dado será alterado nesta tela.")
