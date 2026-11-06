import streamlit as st
from supabase import create_client

st.set_page_config(page_title='Sistema de Gestão Patrimonial IPB - CABO', page_icon='⛪', layout='wide', initial_sidebar_state='expanded')

st.markdown('''<style>
.stApp {background: #f5f7f4;}
[data-testid="stSidebar"] {background: #123f30;}
[data-testid="stSidebar"] * {color: #f6f6f0 !important;}
h1,h2,h3 {color: #174b37;}
.stButton > button[kind="primary"] {background-color: #176747; border-color: #176747;}
</style>''', unsafe_allow_html=True)

@st.cache_resource
def client():
    return create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_ANON_KEY'])

def logout():
    for key in ('access_token','refresh_token','profile','user_id'):
        st.session_state.pop(key, None)
    st.rerun()

def current_profile(access_token, user_id):
    # The user JWT, not the service-role key, enforces RLS.
    from postgrest import SyncPostgrestClient
    url = st.secrets['SUPABASE_URL'].rstrip('/') + '/rest/v1'
    api = SyncPostgrestClient(url, headers={
        'apikey': st.secrets['SUPABASE_ANON_KEY'],
        'Authorization': 'Bearer ' + access_token,
    })
    result = api.from_('perfis').select('id,nome_completo,papel,ativo').eq('id',user_id).single().execute()
    return result.data

def authenticate(email, password):
    # A fresh client avoids sharing mutable authentication state between sessions.
    auth_client = create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_ANON_KEY'])
    result = auth_client.auth.sign_in_with_password({'email':email, 'password':password})
    if not result.session or not result.user:
        raise ValueError('Não foi possível autenticar.')
    profile = current_profile(result.session.access_token, result.user.id)
    if not profile or not profile.get('ativo'):
        raise PermissionError('Sua conta não está autorizada a acessar o sistema.')
    st.session_state['access_token'] = result.session.access_token
    st.session_state['refresh_token'] = result.session.refresh_token
    st.session_state['user_id'] = result.user.id
    st.session_state['profile'] = profile

st.title('⛪ Sistema de Gestão Patrimonial IPB - CABO')

if 'access_token' not in st.session_state:
    st.subheader('Acesso ao sistema')
    st.write('Entre com a conta criada pelo administrador.')
    with st.form('login'):
        email = st.text_input('E-mail')
        password = st.text_input('Senha', type='password')
        submitted = st.form_submit_button('Entrar', type='primary', use_container_width=True)
    if submitted:
        try:
            authenticate(email.strip(), password)
            st.rerun()
        except Exception:
            st.error('Não foi possível entrar. Verifique suas credenciais e se sua conta está ativa.')
    st.stop()

try:
    # Refresh token and recheck the profile on every rerun.
    session_client = create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_ANON_KEY'])
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
    st.header('IPB - CABO')
    st.write(profile['nome_completo'])
    st.caption('Perfil: ' + profile['papel'])
    page = st.radio('Menu', ['Painel principal','Patrimônios','Empréstimos','Devoluções','Relatórios','Usuários'], label_visibility='collapsed')
    st.divider()
    if st.button('Sair', use_container_width=True):
        logout()

if page == 'Painel principal':
    st.header('Painel principal')
    st.success('Login validado pelo Supabase. Bem-vindo ao sistema!')
    st.info('Próxima etapa: cadastro e consulta de patrimônios.')
elif page == 'Usuários' and profile['papel'] != 'admin':
    st.error('Acesso restrito ao administrador.')
else:
    st.header(page)
    st.info('Módulo em desenvolvimento. Nenhum dado será alterado nesta tela.')
