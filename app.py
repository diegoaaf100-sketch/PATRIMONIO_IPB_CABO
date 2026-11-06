import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import streamlit as st
from PIL import Image
from postgrest import SyncPostgrestClient
from supabase import create_client


st.set_page_config(
    page_title="Sistema de Gestão Patrimonial IPB - CABO",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets" / "logo_ipb.png"
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
    for chave in ("access_token", "refresh_token", "user_id", "profile"):
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
    })


def validar_sessao():
    if not st.session_state.get("refresh_token"):
        return False
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
            .select("id,codigo,descricao,categoria_id,localizacao_id,marca,modelo,numero_serie,data_aquisicao,valor_aquisicao,estado_conservacao,situacao,observacoes,criado_em,atualizado_em")
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


def formulario_patrimonio(chave, categorias, localizacoes, registro=None):
    edicao = registro is not None
    categorias_map = opcoes_referencia(categorias)
    locais_map = opcoes_referencia(localizacoes)
    cat_ids = [""] + list(categorias_map)
    loc_ids = [""] + list(locais_map)
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
        payload = {
            "descricao": descricao.strip(),
            "categoria_id": id_opcional(categoria),
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
            st.success("Patrimônio atualizado com sucesso!")
        else:
            # O trigger BEFORE INSERT do Supabase substitui este código temporário.
            # A coluna codigo é NOT NULL e não tem DEFAULT no esquema atual.
            payload["codigo"] = "PENDENTE"
            payload["criado_por"] = st.session_state["user_id"]
            resposta = api.from_("patrimonios").insert(payload).execute()
            if not resposta.data:
                st.error("O Supabase não retornou o patrimônio cadastrado.")
                return
            codigo = resposta.data[0].get("codigo", "")
            if codigo == "PENDENTE":
                st.warning("Cadastro realizado, mas o gatilho de numeração não atribuiu um código. Verifique o trigger no Supabase.")
            else:
                st.success(f"Patrimônio cadastrado! Código: {codigo}")
        st.session_state["patrimonio_atualizado"] = True
    except ValueError as erro:
        st.error(str(erro))
    except Exception as erro:
        LOG.warning("Falha ao salvar patrimônio: %s", type(erro).__name__)
        st.error(f"Não foi possível salvar ({type(erro).__name__}). Confira as permissões e as regras do Supabase.")


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
    abas = ["Consultar patrimônios"] + (["Cadastrar patrimônio", "Editar patrimônio"] if pode_gerenciar else [])
    tabs = st.tabs(abas)
    with tabs[0]:
        busca = st.text_input("Pesquisar", placeholder="Código, descrição, marca, modelo ou número de série")
        categorias_map = opcoes_referencia(categorias)
        locais_map = opcoes_referencia(locais)
        categorias_filtro = ["Todas"] + sorted(set(categorias_map.values()))
        situacoes_filtro = ["Todas"] + sorted({r.get("situacao") or "" for r in registros if r.get("situacao")})
        fc, fs = st.columns(2)
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
            filtrados.append({
                "Código": r.get("codigo"),
                "Descrição": r.get("descricao"),
                "Categoria": categorias_map.get(r.get("categoria_id"), "—"),
                "Localização": locais_map.get(r.get("localizacao_id"), "—"),
                "Marca": r.get("marca") or "—",
                "Situação": r.get("situacao") or "—",
                "Conservação": r.get("estado_conservacao") or "—",
            })
        st.caption(f"{len(filtrados)} patrimônio(s) encontrado(s)")
        st.dataframe(filtrados, use_container_width=True, hide_index=True)
    if pode_gerenciar:
        with tabs[1]:
            formulario_patrimonio("form_cadastro_patrimonio", categorias, locais)
        with tabs[2]:
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
    if st.session_state.pop("patrimonio_atualizado", False):
        st.caption("Para atualizar a tabela de consulta, clique em Patrimônios novamente no menu.")


def painel_principal(nome):
    st.header("Painel principal")
    st.success(f"Bem-vindo(a), {nome}!")
    try:
        registros = listar_patrimonios()
    except Exception as erro:
        LOG.warning("Falha ao carregar indicadores: %s", type(erro).__name__)
        st.warning("Não foi possível carregar os indicadores do Supabase.")
        return
    contagens = {
        "Patrimônios": len(registros),
        "Disponíveis": sum(r.get("situacao") == "disponivel" for r in registros),
        "Emprestados": sum(r.get("situacao") == "emprestado" for r in registros),
        "Em manutenção": sum(r.get("situacao") == "manutencao" for r in registros),
    }
    for coluna, (titulo, valor) in zip(st.columns(4), contagens.items()):
        with coluna:
            st.metric(titulo, valor)
    st.caption("Indicadores calculados a partir dos registros do Supabase.")


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
    mostrar_logo(105)
    st.header("IPB - CABO")
    st.caption("Gestão Patrimonial")
    st.divider()
    st.write("**Usuário:**", nome)
    st.caption("Perfil: " + papel.upper())
    st.divider()
    paginas = ["Painel principal", "Patrimônios", "Empréstimos", "Devoluções", "Relatórios"]
    if papel == "admin":
        paginas.append("Usuários")
    pagina = st.radio("Navegação", paginas, label_visibility="collapsed")
    st.divider()
    if st.button("Sair do sistema", use_container_width=True):
        limpar_sessao()
        st.rerun()

st.markdown("""
<div class="ipb-banner">
<h1>Sistema de Gestão Patrimonial IPB - CABO</h1>
<p>Controle e administração dos bens patrimoniais</p>
</div>
""", unsafe_allow_html=True)

if pagina == "Painel principal":
    painel_principal(nome)
elif pagina == "Patrimônios":
    pagina_patrimonios(papel)
elif pagina == "Usuários":
    if papel != "admin":
        st.error("Acesso restrito ao administrador.")
        st.stop()
    st.header("Administração de usuários")
    st.info("Módulo em desenvolvimento. Usuários ainda não podem ser criados nesta tela.")
else:
    st.header(pagina)
    st.info("Módulo em desenvolvimento. Nenhum dado será alterado nesta tela.")
