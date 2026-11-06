import streamlit as st
from pathlib import Path
from datetime import date
from decimal import Decimal, InvalidOperation
from PIL import Image
from supabase import create_client
from postgrest import SyncPostgrestClient

st.set_page_config(page_title="Sistema de Gestão Patrimonial IPB - CABO", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")
BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "assets" / "logo_ipb.png"

st.markdown("""
<style>
:root { color-scheme: dark; }
.stApp, [data-testid="stAppViewContainer"] { background: #073f30 !important; color: #fff !important; }
[data-testid="stHeader"] { background: rgba(7,63,48,.96) !important; }
[data-testid="stSidebar"] { background: #052f25 !important; border-right: 1px solid #26674f; }
[data-testid="stSidebar"] * { color: #fff !important; }
h1,h2,h3,h4,p, label, [data-testid="stCaptionContainer"] { color: #fff !important; }
[data-testid="stForm"], [data-testid="stMetric"] { background: #fff !important; color: #073f30 !important; border: 1px solid #d9e9df; border-radius: 16px; padding: 18px; }
[data-testid="stForm"] label, [data-testid="stForm"] p, [data-testid="stMetric"] *, [data-testid="stForm"] [data-testid="stWidgetLabel"] { color: #073f30 !important; }
[data-testid="stForm"] input, [data-testid="stForm"] textarea { color: #073f30 !important; }
[data-testid="stForm"] [data-baseweb="select"] * { color: #073f30; }
[data-testid="stFormSubmitButton"] button, .stButton button[kind="primary"] { background: #006341 !important; border: 1px solid #006341 !important; color: #fff !important; border-radius: 10px; font-weight: 700; }
[data-testid="stFormSubmitButton"] button *, .stButton button[kind="primary"] * { color: #fff !important; }
[data-testid="stFormSubmitButton"] button:hover, .stButton button[kind="primary"]:hover { background: #004d32 !important; }
[data-testid="stMetric"] [data-testid="stMetricLabel"] *, [data-testid="stMetric"] [data-testid="stMetricValue"] { color: #073f30 !important; }
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
[data-testid="stSidebar"] [role="radiogroup"] label { border-radius: 10px; padding: 7px 9px; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #176247; }
[data-testid="stAlert"] p { color: inherit !important; }
@media(max-width:768px){[data-testid="stForm"]{padding:12px!important}}
</style>
""", unsafe_allow_html=True)


def mostrar_logo(largura=130):
    if LOGO_PATH.is_file():
        try:
            with Image.open(LOGO_PATH) as img:
                st.image(img.copy(), width=largura)
        except Exception:
            st.caption("IPB - CABO")
    else:
        st.caption("IPB - CABO")


def cliente():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])


def api_usuario():
    """Todas as consultas e gravações usam o JWT do usuário e respeitam RLS."""
    return SyncPostgrestClient(
        st.secrets["SUPABASE_URL"].rstrip("/") + "/rest/v1",
        headers={
            "apikey": st.secrets["SUPABASE_ANON_KEY"],
            "Authorization": "Bearer " + st.session_state["access_token"],
        },
    )


def consultar_perfil(token, user_id):
    api = SyncPostgrestClient(
        st.secrets["SUPABASE_URL"].rstrip("/") + "/rest/v1",
        headers={"apikey": st.secrets["SUPABASE_ANON_KEY"], "Authorization": "Bearer " + token},
    )
    result = api.from_("perfis").select("id,nome_completo,papel,ativo").eq("id", user_id).limit(1).execute()
    return result.data[0] if result.data else None


def limpar_sessao():
    for k in ("access_token", "refresh_token", "user_id", "profile"):
        st.session_state.pop(k, None)


def autenticar(email, senha):
    response = cliente().auth.sign_in_with_password({"email": email, "password": senha})
    if not response.session or not response.user:
        raise ValueError("Credenciais não validadas")
    perfil = consultar_perfil(response.session.access_token, response.user.id)
    if not perfil or not perfil.get("ativo"):
        raise PermissionError("Usuário sem perfil ativo")
    st.session_state.update(access_token=response.session.access_token,
                            refresh_token=response.session.refresh_token,
                            user_id=response.user.id, profile=perfil)


def validar_sessao():
    if not st.session_state.get("refresh_token"):
        return False
    try:
        response = cliente().auth.refresh_session(st.session_state["refresh_token"])
        if not response.session or not response.user or response.user.id != st.session_state.get("user_id"):
            return False
        perfil = consultar_perfil(response.session.access_token, response.user.id)
        if not perfil or not perfil.get("ativo"):
            return False
        st.session_state.update(access_token=response.session.access_token,
                                refresh_token=response.session.refresh_token, profile=perfil)
        return True
    except Exception:
        return False


def tela_login():
    _, meio, _ = st.columns([1, 1.4, 1])
    with meio:
        mostrar_logo(140)
        st.title("Sistema de Gestão Patrimonial")
        st.markdown("**IPB - CABO**")
        st.caption("Acesso restrito a usuários autorizados")
        with st.form("login"):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            enviar = st.form_submit_button("Entrar no sistema", type="primary", use_container_width=True)
        if enviar:
            if not email.strip() or not senha:
                st.warning("Informe e-mail e senha.")
            else:
                try:
                    autenticar(email.strip(), senha)
                    st.rerun()
                except PermissionError:
                    st.error("Sua conta não está autorizada ou está inativa.")
                except Exception:
                    st.error("Não foi possível entrar. Verifique suas credenciais e a conexão com o Supabase.")
    st.stop()


def listar_opcoes(tabela):
    dados = api_usuario().from_(tabela).select("id,nome,ativo").eq("ativo", True).order("nome").execute().data or []
    return {item["nome"]: item["id"] for item in dados}


def listar_patrimonios():
    # Paginação evita o limite padrão de 1000 linhas por resposta.
    todos = []
    inicio = 0
    while True:
        lote = (api_usuario().from_("patrimonios")
                .select("id,codigo,descricao,categoria_id,localizacao_id,marca,modelo,numero_serie,data_aquisicao,valor_aquisicao,estado_conservacao,situacao,observacoes,criado_em")
                .order("codigo").range(inicio, inicio + 499).execute().data or [])
        todos.extend(lote)
        if len(lote) < 500:
            break
        inicio += 500
    return todos


def texto_ou_nulo(valor):
    return valor.strip() or None


def valor_monetario(valor):
    valor = valor.strip().replace("R$", "").replace(" ", "")
    if not valor:
        return None
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    numero = Decimal(valor)
    if not numero.is_finite() or numero < 0:
        raise InvalidOperation
    return str(numero.quantize(Decimal("0.01")))


def formulario_patrimonio(categorias, localizacoes, atual=None):
    editando = atual is not None
    cat_por_id = {v: k for k, v in categorias.items()}
    loc_por_id = {v: k for k, v in localizacoes.items()}
    lista_cat = ["Não informada"] + list(categorias)
    lista_loc = ["Não informada"] + list(localizacoes)
    cat_atual = cat_por_id.get((atual or {}).get("categoria_id"), "Não informada")
    loc_atual = loc_por_id.get((atual or {}).get("localizacao_id"), "Não informada")
    with st.form("editar_bem" if editando else "novo_bem", clear_on_submit=not editando):
        if editando:
            st.caption("Código patrimonial: " + atual["codigo"] + " (não pode ser alterado)")
        else:
            st.caption("Código gerado automaticamente pelo Supabase ao salvar.")
        descricao = st.text_input("Descrição do patrimônio *", value=(atual or {}).get("descricao") or "")
        c1, c2 = st.columns(2)
        with c1:
            categoria = st.selectbox("Categoria", lista_cat, index=lista_cat.index(cat_atual))
        with c2:
            localizacao = st.selectbox("Localização", lista_loc, index=lista_loc.index(loc_atual))
        c3, c4 = st.columns(2)
        with c3:
            marca = st.text_input("Marca", value=(atual or {}).get("marca") or "")
            numero_serie = st.text_input("Número de série", value=(atual or {}).get("numero_serie") or "")
        with c4:
            modelo = st.text_input("Modelo", value=(atual or {}).get("modelo") or "")
            conservacao_atual = (atual or {}).get("estado_conservacao") or "Não informado"
            estados = ["Não informado", "Novo", "Bom", "Regular", "Ruim"]
            if conservacao_atual not in estados:
                estados.append(conservacao_atual)
            conservacao = st.selectbox("Estado de conservação", estados, index=estados.index(conservacao_atual))
        c5, c6 = st.columns(2)
        with c5:
            data_original = (atual or {}).get("data_aquisicao")
            informar_data = st.checkbox("Informar data de aquisição", value=bool(data_original))
            data_aquisicao = st.date_input("Data de aquisição", value=date.fromisoformat(data_original) if data_original else date.today(), disabled=not informar_data)
        with c6:
            valor_original = (atual or {}).get("valor_aquisicao")
            valor = st.text_input("Valor de aquisição (R$)", value=str(valor_original).replace(".", ",") if valor_original is not None else "", placeholder="Ex.: 1.250,00")
        observacoes = st.text_area("Observações", value=(atual or {}).get("observacoes") or "")
        enviado = st.form_submit_button("Salvar alterações" if editando else "Cadastrar patrimônio", type="primary", use_container_width=True)
    if not enviado:
        return
    if not descricao.strip():
        st.warning("Preencha a descrição do patrimônio.")
        return
    try:
        valor_final = valor_monetario(valor)
    except (InvalidOperation, ValueError):
        st.error("Valor de aquisição inválido. Use, por exemplo, 1250,00.")
        return
    dados = {
        "descricao": descricao.strip(), "categoria_id": categorias.get(categoria),
        "localizacao_id": localizacoes.get(localizacao), "marca": texto_ou_nulo(marca),
        "modelo": texto_ou_nulo(modelo), "numero_serie": texto_ou_nulo(numero_serie),
        "data_aquisicao": data_aquisicao.isoformat() if informar_data else None,
        "valor_aquisicao": valor_final,
        "estado_conservacao": None if conservacao == "Não informado" else conservacao,
        "observacoes": texto_ou_nulo(observacoes),
    }
    try:
        if editando:
            dados["atualizado_por"] = st.session_state["user_id"]
            resultado = (api_usuario().from_("patrimonios").update(dados)
                         .eq("id", atual["id"]).select("id,codigo").execute().data or [])
            if not resultado:
                st.error("Nenhum registro foi atualizado. Verifique suas permissões RLS.")
                return
            st.success("Patrimônio atualizado com sucesso!")
        else:
            dados["criado_por"] = st.session_state["user_id"]
            # A trigger SQL atribui o código; não enviar código manual.
            resultado = api_usuario().from_("patrimonios").insert(dados).select("id,codigo").execute().data or []
            if not resultado:
                st.error("O banco não retornou o patrimônio cadastrado. Confira as políticas RLS.")
                return
            st.success("Patrimônio cadastrado! Código: " + resultado[0]["codigo"])
            st.session_state["ultimo_codigo"] = resultado[0]["codigo"]
    except Exception as exc:
        st.error("Não foi possível salvar. Confira permissões, campos e se o SQL de numeração já foi executado.")
        with st.expander("Detalhes técnicos do erro"):
            st.code(str(exc))


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
        limpar_sessao()
        st.rerun()

st.title("Sistema de Gestão Patrimonial IPB - CABO")
st.caption("Controle e administração dos bens patrimoniais")
st.divider()

if pagina == "Painel principal":
    st.header("Painel principal")
    st.success(f"Bem-vindo(a), {perfil.get('nome_completo') or 'usuário'}!")
    try:
        bens = listar_patrimonios()
        indicadores = [
            ("Patrimônios", len(bens)),
            ("Disponíveis", sum(x.get("situacao") == "disponivel" for x in bens)),
            ("Emprestados", sum(x.get("situacao") == "emprestado" for x in bens)),
            ("Em manutenção", sum(str(x.get("situacao", "")).startswith("manut") for x in bens)),
        ]
        for coluna, (nome, valor) in zip(st.columns(4), indicadores):
            with coluna:
                st.metric(nome, valor)
    except Exception:
        st.warning("Não foi possível carregar os indicadores. Verifique a conexão e as permissões.")
elif pagina == "Patrimônios":
    st.header("Patrimônios")
    try:
        categorias = listar_opcoes("categorias")
        localizacoes = listar_opcoes("localizacoes")
        bens = listar_patrimonios()
    except Exception as exc:
        st.error("Não foi possível consultar os dados do Supabase.")
        with st.expander("Detalhes técnicos"):
            st.code(str(exc))
        st.stop()
    abas = st.tabs(["Consultar patrimônios", "Cadastrar patrimônio", "Editar patrimônio"])
    with abas[0]:
        busca = st.text_input("Pesquisar por código, descrição, marca ou número de série", key="busca_bens")
        filtro = st.selectbox("Situação", ["Todas"] + sorted({x.get("situacao") for x in bens if x.get("situacao")}))
        filtrados = [x for x in bens if (filtro == "Todas" or x.get("situacao") == filtro) and
                     (not busca or busca.lower() in " ".join(str(x.get(k) or "") for k in ("codigo", "descricao", "marca", "numero_serie")).lower())]
        st.caption(f"{len(filtrados)} patrimônio(s) encontrado(s)")
        nomes_cat = {v: k for k, v in categorias.items()}
        nomes_loc = {v: k for k, v in localizacoes.items()}
        linhas = [{"Código": x["codigo"], "Descrição": x["descricao"], "Categoria": nomes_cat.get(x.get("categoria_id"), "—"),
                   "Localização": nomes_loc.get(x.get("localizacao_id"), "—"), "Situação": x.get("situacao"),
                   "Marca": x.get("marca") or "—"} for x in filtrados]
        st.dataframe(linhas, use_container_width=True, hide_index=True)
    with abas[1]:
        st.subheader("Cadastrar novo patrimônio")
        st.caption("Disponível para usuários com permissão de gestor. O Supabase valida cada gravação.")
        formulario_patrimonio(categorias, localizacoes)
    with abas[2]:
        st.subheader("Editar patrimônio existente")
        if not bens:
            st.info("Ainda não existem patrimônios cadastrados.")
        else:
            por_codigo = {f"{x['codigo']} — {x['descricao']}": x for x in bens}
            escolhido = st.selectbox("Selecione o patrimônio", list(por_codigo), key="selecionar_edicao")
            formulario_patrimonio(categorias, localizacoes, por_codigo[escolhido])
elif pagina == "Usuários":
    if papel != "admin":
        st.error("Acesso restrito ao administrador.")
        st.stop()
    st.header("Administração de usuários")
    st.info("Módulo em desenvolvimento.")
else:
    st.header(pagina)
    st.info("Módulo em desenvolvimento. Nenhum dado será alterado nesta tela.")
