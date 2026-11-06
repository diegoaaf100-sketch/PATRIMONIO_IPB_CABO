from pathlib import Path
import streamlit as st
from supabase import create_client
from postgrest import SyncPostgrestClient

st.set_page_config(page_title='Sistema de Gestão Patrimonial IPB - CABO', page_icon='🌿', layout='wide', initial_sidebar_state='expanded')

st.markdown('''<style>
.stApp {background:#f4f7f4;}
[data-testid="stSidebar"] {background:#07583f;}
[data-testid="stSidebar"] * {color:#f6f6f0 !important;}
h1,h2,h3 {color:#123f30;}
.stButton > button[kind="primary"], .stFormSubmitButton button[kind="primary"] {background:#08734d !important; border-color:#08734d !important; color:white !important; border-radius:9px;}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton button[kind="primary"]:hover {background:#065c3d !important;}
[data-testid="stForm"] {border:1px solid #dbe7df; border-radius:16px; padding:22px; background:white; box-shadow:0 8px 30px rgba(0,45,25,.06);}
</style>''', unsafe_allow_html=True)

URL = st.secrets['SUPABASE_URL']
KEY = st.secrets['SUPABASE_ANON_KEY']


def logout():
    for key in ('access_token', 'refresh_token', 'profile', 'user_id'):
        st.session_state.pop(key, None)
    st.rerun()


def current_profile(access_token, user_id):
    api = SyncPostgrestClient(URL.rstrip('/') + '/rest/v1', headers={
        'apikey': KEY,
        'Authorization': 'Bearer ' + access_token,
    })
    result = api.from_('perfis').select('id,nome_completo,papel,ativo').eq('id', user_id).single().execute()
    return result.data


def authenticate(email, password):
    auth_client = create_client(URL, KEY)
    result = auth_client.auth.sign_in_with_password({'email': email, 'password': password})
    if not result.session or not result.user:
        raise ValueError('Não foi possível autenticar.')
    profile = current_profile(result.session.access_token, result.user.id)
    if not profile or not profile.get('ativo'):
        raise PermissionError('Conta não autorizada.')
    st.session_state.update({
        'access_token': result.session.access_token,
        'refresh_token': result.session.refresh_token,
        'user_id': result.user.id,
        'profile': profile,
    })


if 'access_token' not in st.session_state:
    left, middle, right = st.columns([1, 1.35, 1])
    with middle:
        st.write('')
        st.write('')
        logo = Path(__file__).parent / 'assets' / 'logo_ipb.png'
        if logo.exists():
            _, logo_col, _ = st.columns([1, 1.25, 1])
            with logo_col:
                st.image(str(logo), use_container_width=True)
        st.markdown('<h2 style="text-align:center;margin:10px 0 4px;">Sistema de Gestão Patrimonial</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;color:#08734d;font-weight:700;letter-spacing:2px;">IPB - CABO</p>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;color:#5c6d63;">Acesso restrito a usuários autorizados</p>', unsafe_allow_html=True)
        with st.form('login'):
            email = st.text_input('E-mail', placeholder='Digite seu e-mail')
            password = st.text_input('Senha', type='password', placeholder='Digite sua senha')
            submitted = st.form_submit_button('Entrar no sistema', type='primary', use_container_width=True)
        if submitted:
            try:
                authenticate(email.strip(), password)
                st.rerun()
            except Exception:
                st.error('Não foi possível entrar. Verifique suas credenciais e se sua conta está ativa.')
    st.stop()

try:
    session_client = create_client(URL, KEY)
    refreshed = session_client.auth.refresh_session(st.session_state['refresh_token'])
    if not refreshed.session:
        raise ValueError('Sessão expirada')
    st.session_state['access_token'] = refreshed.session.access_token
    st.session_state['refresh_token'] = refreshed.session.refresh_token
    st.session_state['profile'] = current_profile(refreshed.session.access_token, st.session_state['user_id'])
    if not st.session_state['profile'] or not st.session_state['profile'].get('ativo'):
        raise PermissionError('Conta desativada')
except Exception:
    logout()

profile = st.session_state['profile']
with st.sidebar:
    logo = Path(__file__).parent / 'assets' / 'logo_ipb.png'
    if logo.exists():
        st.image(str(logo), width=110)
    st.header('IPB - CABO')
    st.write(profile['nome_completo'])
    st.caption('Perfil: ' + profile['papel'])
    page = st.radio('Menu', ['Painel principal', 'Patrimônios', 'Empréstimos', 'Devoluções', 'Relatórios', 'Usuários'], label_visibility='collapsed')
    st.divider()
    if st.button('Sair', use_container_width=True):
        logout()

st.title('Sistema de Gestão Patrimonial IPB - CABO')
if page == 'Painel principal':
    st.header('Painel principal')
    st.success('Login validado pelo Supabase. Bem-vindo ao sistema!')
    st.info('Próxima etapa: cadastro e consulta de patrimônios.')
elif page == 'Usuários' and profile['papel'] != 'admin':
    st.error('Acesso restrito ao administrador.')
else:
    st.header(page)
    st.info('Módulo em desenvolvimento. Nenhum dado será alterado nesta tela.')
