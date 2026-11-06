
import streamlit as st
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from supabase import create_client
from postgrest import SyncPostgrestClient


# ============================================================
# CONFIGURACOES GERAIS
# ============================================================

st.set_page_config(
    page_title="Sistema de Gestão Patrimonial IPB - CABO",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets" / "logo_ipb.png"

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]


# ============================================================
# IDENTIDADE VISUAL
# ============================================================

st.markdown("""
<style>

/* Fundo geral */
.stApp {
    background-color: #f4f7f5;
}

/* Titulos */
h1, h2, h3 {
    color: #173e30 !important;
}

/* Menu lateral */
[data-testid="stSidebar"] {
    background-color: #123f30;
}

[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

/* Botoes principais */
.stButton button[kind="primary"],
.stFormSubmitButton button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
    background-color: #006341 !important;
    border-color: #006341 !important;
    color: white !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
}

.stButton button[kind="primary"]:hover,
.stFormSubmitButton button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    background-color: #004d32 !important;
    border-color: #004d32 !important;
    color: white !important;
}

/* Campos */
.stTextInput input {
    border-radius: 9px !important;
}

/* Formulario */
[data-testid="stForm"] {
    background-color: #ffffff;
    border: 1px solid #dce7df;
    border-radius: 16px;
    padding: 22px;
    box-shadow: 0 8px 28px rgba(0, 50, 25, 0.06);
}

/* Aparencia dos cards */
[data-testid="stMetric"] {
    background: white;
    padding: 18px;
    border: 1px solid #dce7df;
    border-radius: 14px;
}

/* Ajustes para celular */
@media (max-width: 768px) {
    h1 {
        font-size: 1.65rem !important;
    }

    [data-testid="stForm"] {
        padding: 12px;
    }
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# LOGO
# ============================================================

def mostrar_logo(largura=145):
    """Exibe a logo sem interromper o sistema se houver erro."""

    if not LOGO_PATH.is_file():
        return

    try:
        with Image.open(LOGO_PATH) as imagem:
            imagem.load()
            st.image(imagem.copy(), width=largura)

    except (UnidentifiedImageError, OSError, ValueError):
        # A aplicacao continua funcionando mesmo sem a imagem.
        pass


# ============================================================
# SUPABASE
# ============================================================

def criar_cliente():
    """Cria um cliente independente para cada operacao."""
    return create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY
    )


def consultar_perfil(access_token, user_id):
    """Consulta o perfil usando o token do usuario."""

    api = SyncPostgrestClient(
        SUPABASE_URL.rstrip("/") + "/rest/v1",
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {access_token}"
        }
    )

    resultado = (
        api.from_("perfis")
        .select("id,nome_completo,papel,ativo")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )

    if not resultado.data:
        return None

    return resultado.data[0]


# ============================================================
# LOGIN E LOGOUT
# ============================================================

def logout():

    for chave in (
        "access_token",
        "refresh_token",
        "user_id",
        "profile"
    ):
        st.session_state.pop(chave, None)

    st.rerun()


def autenticar(email, senha):

    cliente = criar_cliente()

    resultado = cliente.auth.sign_in_with_password({
        "email": email,
        "password": senha
    })

    if not resultado.session or not resultado.user:
        raise ValueError("Falha na autenticacao.")

    perfil = consultar_perfil(
        resultado.session.access_token,
        resultado.user.id
    )

    if not perfil or not perfil.get("ativo"):
        raise PermissionError("Usuario sem autorizacao.")

    st.session_state["access_token"] = (
        resultado.session.access_token
    )

    st.session_state["refresh_token"] = (
        resultado.session.refresh_token
    )

    st.session_state["user_id"] = resultado.user.id
    st.session_state["profile"] = perfil


def validar_sessao():

    if "refresh_token" not in st.session_state:
        return False

    try:
        cliente = criar_cliente()

        resultado = cliente.auth.refresh_session(
            st.session_state["refresh_token"]
        )

        if not resultado.session:
            return False

        st.session_state["access_token"] = (
            resultado.session.access_token
        )

        st.session_state["refresh_token"] = (
            resultado.session.refresh_token
        )

        perfil = consultar_perfil(
            resultado.session.access_token,
            st.session_state["user_id"]
        )

        if not perfil or not perfil.get("ativo"):
            return False

        st.session_state["profile"] = perfil
        return True

    except Exception:
        return False


# ============================================================
# TELA DE LOGIN
# ============================================================

def tela_login():

    st.markdown("<div style='height:20px'></div>",
                unsafe_allow_html=True)

    esquerda, centro, direita = st.columns(
        [1, 1.25, 1]
    )

    with centro:

        # Logo centralizada
        logo_esquerda, logo_centro, logo_direita = (
            st.columns([1, 1, 1])
        )

        with logo_centro:
            mostrar_logo(145)

        st.markdown(
            """
            <h1 style="
                text-align:center;
                font-size:32px;
                margin-bottom:5px;
                color:#173e30;
            ">
                Sistema de Gestão<br>Patrimonial
            </h1>

            <p style="
                text-align:center;
                color:#006341;
                font-weight:700;
                letter-spacing:3px;
                margin-top:8px;
            ">
                IPB - CABO
            </p>

            <p style="
                text-align:center;
                color:#66756d;
                margin-bottom:25px;
            ">
                Acesso restrito a usuários autorizados
            </p>
            """,
            unsafe_allow_html=True
        )

        with st.form("form_login"):

            email = st.text_input(
                "E-mail",
                placeholder="Digite seu e-mail"
            )

            senha = st.text_input(
                "Senha",
                type="password",
                placeholder="Digite sua senha"
            )

            entrar = st.form_submit_button(
                "Entrar no sistema",
                type="primary",
                use_container_width=True
            )

        if entrar:

            if not email.strip() or not senha:
                st.warning("Informe o e-mail e a senha.")

            else:
                try:
                    autenticar(email.strip(), senha)
                    st.rerun()

                except Exception:
                    st.error(
                        "Não foi possível entrar. "
                        "Verifique suas credenciais "
                        "e se sua conta está ativa."
                    )

    st.stop()


# ============================================================
# VERIFICACAO DE ACESSO
# ============================================================

if "access_token" not in st.session_state:
    tela_login()

if not validar_sessao():
    logout()

perfil = st.session_state["profile"]
papel = perfil["papel"]


# ============================================================
# MENU LATERAL
# ============================================================

with st.sidebar:

    mostrar_logo(105)

    st.markdown("### IPB - CABO")
    st.caption("Gestão Patrimonial")

    st.divider()

    st.write("**Usuário conectado:**")
    st.write(perfil["nome_completo"])

    st.caption(
        f"Perfil de acesso: {papel.upper()}"
    )

    st.divider()

    paginas = [
        "Painel principal",
        "Patrimônios",
        "Empréstimos",
        "Devoluções",
        "Relatórios"
    ]

    if papel == "admin":
        paginas.append("Usuários")

    pagina = st.radio(
        "Navegação",
        paginas,
        label_visibility="collapsed"
    )

    st.divider()

    if st.button(
        "Sair do sistema",
        use_container_width=True
    ):
        logout()


# ============================================================
# CABECALHO
# ============================================================

st.title("Sistema de Gestão Patrimonial IPB - CABO")
st.caption("Controle e administração dos bens patrimoniais")

st.divider()


# ============================================================
# PAINEL PRINCIPAL
# ============================================================

if pagina == "Painel principal":

    st.header("Painel principal")

    st.success(
        f"Bem-vindo(a), {perfil['nome_completo']}!"
    )

    st.info(
        "Sistema conectado ao Supabase. "
        "Os módulos de gestão patrimonial "
        "serão habilitados nas próximas etapas."
    )

    coluna1, coluna2, coluna3, coluna4 = st.columns(4)

    with coluna1:
        st.metric("Patrimônios", "—")

    with coluna2:
        st.metric("Disponíveis", "—")

    with coluna3:
        st.metric("Emprestados", "—")

    with coluna4:
        st.metric("Em manutenção", "—")

    st.caption(
        "Os indicadores serão conectados ao banco "
        "quando o módulo de patrimônios estiver pronto."
    )


# ============================================================
# PATRIMONIOS
# ============================================================

elif pagina == "Patrimônios":

    st.header("Cadastro de patrimônios")

    st.info(
        "Nesta área será possível cadastrar, consultar, "
        "editar e identificar os bens da igreja."
    )

    st.write("Funcionalidades previstas:")
    st.write("• Cadastro individual de bens")
    st.write("• Importação de planilhas Excel")
    st.write("• Geração de código patrimonial")
    st.write("• Etiquetas com QR Code")
    st.write("• Fotografias e documentos")


# ============================================================
# EMPRESTIMOS
# ============================================================

elif pagina == "Empréstimos":

    st.header("Controle de empréstimos")

    st.info(
        "Módulo em desenvolvimento. "
        "Nenhum empréstimo será registrado nesta tela."
    )

    st.write("• Registro de pessoas e organizações")
    st.write("• Seleção de patrimônios")
    st.write("• Emissão de recibos em PDF")
    st.write("• Controle de responsáveis")
    st.write("• Anexação de recibos assinados")


# ============================================================
# DEVOLUCOES
# ============================================================

elif pagina == "Devoluções":

    st.header("Controle de devoluções")

    st.info(
        "Módulo em desenvolvimento. "
        "Nenhuma devolução será registrada nesta tela."
    )

    st.write("• Consulta de empréstimos ativos")
    st.write("• Registro da data de devolução")
    st.write("• Estado de conservação")
    st.write("• Comprovante de devolução")


# ============================================================
# RELATORIOS
# ============================================================

elif pagina == "Relatórios":

    st.header("Relatórios patrimoniais")

    st.info(
        "Os relatórios serão implementados "
        "nas próximas etapas."
    )

    st.write("• Inventário completo")
    st.write("• Histórico de empréstimos")
    st.write("• Bens por localização")
    st.write("• Bens por categoria")
    st.write("• Relatório de auditoria")


# ============================================================
# USUARIOS
# ============================================================

elif pagina == "Usuários":

    if papel != "admin":
        st.error("Acesso restrito ao administrador.")
        st.stop()

    st.header("Administração de usuários")

    st.info(
        "A criação de usuários será realizada "
        "exclusivamente pelo administrador."
    )

    st.write("• Cadastro de usuários")
    st.write("• Perfis e permissões")
    st.write("• Ativação e desativação de contas")
    st.write("• Histórico de atividades")
