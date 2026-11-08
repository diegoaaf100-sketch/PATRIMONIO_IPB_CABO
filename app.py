import logging
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
    abas = ["Consultar patrimônios"] + (["Cadastrar patrimônio", "Editar patrimônio"] if pode_gerenciar else [])
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
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from xml.sax.saxutils import escape

    saida = BytesIO()
    doc = SimpleDocTemplate(saida, pagesize=A4, rightMargin=1.8*cm, leftMargin=1.8*cm, topMargin=1.8*cm, bottomMargin=1.8*cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="IPBTitulo", parent=styles["Title"], textColor=colors.HexColor("#075039"), alignment=TA_CENTER, fontSize=15, spaceAfter=12))
    styles.add(ParagraphStyle(name="IPBCorpo", parent=styles["BodyText"], fontSize=10, leading=15, spaceAfter=8))
    corpo = lambda s: Paragraph(escape(str(s or "—")), styles["IPBCorpo"])
    conteudo = [Paragraph("IGREJA PRESBITERIANA DO BRASIL — IPB CABO", styles["IPBTitulo"]),
                Paragraph(f"RECIBO DE EMPRÉSTIMO Nº {emprestimo['numero']}", styles["Heading2"]), Spacer(1, 0.2*cm),
                corpo(f"Recebedor: {pessoa.get('nome', '')}"),
                corpo(f"Documento: {pessoa.get('documento') or 'Não informado'}"),
                corpo(f"Telefone: {pessoa.get('telefone') or 'Não informado'}"),
                corpo(f"Data de retirada: {emprestimo.get('data_retirada') or '—'}"),
                corpo(f"Previsão de devolução: {emprestimo.get('data_prevista_devolucao') or 'Não definida'}"),
                corpo(f"Finalidade: {emprestimo.get('finalidade') or 'Não informada'}"),
                Paragraph("Bens entregues", styles["Heading3"])]
    linhas = [["Código", "Descrição", "Conservação"]]
    for bem in bens:
        linhas.append([corpo(bem.get("codigo")), corpo(bem.get("descricao")), corpo(bem.get("estado_conservacao") or "Não informado")])
    tabela = Table(linhas, colWidths=[3.3*cm, 9.1*cm, 3.5*cm], repeatRows=1, hAlign="LEFT")
    tabela.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,0),colors.HexColor("#dcece2")), ("GRID",(0,0),(-1,-1),0.4,colors.grey), ("VALIGN",(0,0),(-1,-1),"TOP"), ("LEFTPADDING",(0,0),(-1,-1),6), ("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    conteudo.extend([tabela, Spacer(1,0.5*cm), corpo(f"Observações: {emprestimo.get('observacoes') or 'Nenhuma'}"),
                     corpo("Declaro ter recebido os bens relacionados acima e comprometo-me a devolvê-los nas condições acordadas."),
                     Spacer(1, 1.4*cm)])
    assinaturas = Table([
        ["________________________________", "________________________________"],
        [corpo(emprestimo.get("responsavel_entrega")), corpo(emprestimo.get("responsavel_recebimento"))],
        ["Responsável pela entrega", "Responsável pelo recebimento"],
    ], colWidths=[8*cm, 8*cm], hAlign="CENTER")
    assinaturas.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"), ("VALIGN",(0,0),(-1,-1),"TOP")]))
    conteudo.append(KeepTogether(assinaturas))
    doc.build(conteudo)
    return saida.getvalue()


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
        opcoes = ["Novo empréstimo", "Cadastrar pessoa"] + opcoes
    aba_pendente = st.session_state.pop("emprestimo_aba_pendente", None)
    if aba_pendente in opcoes:
        st.session_state["emprestimo_aba"] = aba_pendente
    aba = st.radio("Área de empréstimos", opcoes, horizontal=True, key="emprestimo_aba")
    pessoas_map = {p["id"]: p for p in pessoas}
    bens_map = {b["id"]: b for b in bens}

    if aba == "Cadastrar pessoa":
        with st.form("cadastro_pessoa_ipb"):
            tipo = st.selectbox("Tipo de cadastro", ["pessoa_fisica", "organizacao"], format_func=lambda v: "Pessoa física" if v == "pessoa_fisica" else "Organização")
            nome = st.text_input("Nome completo ou nome da organização *")
            documento = st.text_input("CPF/CNPJ (opcional)")
            telefone = st.text_input("Telefone")
            email = st.text_input("E-mail")
            endereco = st.text_area("Endereço")
            observacoes = st.text_area("Observações")
            salvar = st.form_submit_button("Cadastrar pessoa", type="primary", use_container_width=True)
        if salvar:
            if not nome.strip():
                st.error("Informe o nome da pessoa ou organização.")
            else:
                try:
                    api_usuario(st.session_state["access_token"]).from_("pessoas").insert({
                        "tipo": tipo, "nome": nome.strip(), "documento": documento.strip() or None,
                        "telefone": telefone.strip() or None, "email": email.strip() or None,
                        "endereco": endereco.strip() or None, "observacoes": observacoes.strip() or None,
                        "criado_por": st.session_state["user_id"]
                    }).execute()
                except Exception as erro:
                    LOG.warning("Erro ao cadastrar pessoa: %s", type(erro).__name__)
                    st.error(f"Não foi possível cadastrar a pessoa ({type(erro).__name__}).")
                else:
                    st.session_state["mensagem_emprestimo"] = "Pessoa cadastrada com sucesso!"
                    st.session_state["emprestimo_aba_pendente"] = "Novo empréstimo"
                    st.rerun()

    elif aba == "Novo empréstimo":
        disponiveis = [b for b in bens if b.get("situacao") == "disponivel"]
        if not pessoas:
            st.info("Cadastre primeiro a pessoa ou organização que receberá os bens.")
        elif not disponiveis:
            st.info("Não existem patrimônios disponíveis para empréstimo.")
        else:
            with st.form("novo_emprestimo_ipb"):
                pessoa_id = st.selectbox("Pessoa ou organização que receberá *", list(pessoas_map), format_func=lambda i: pessoas_map[i]["nome"])
                ids = st.multiselect("Selecione um ou mais patrimônios disponíveis *", [b["id"] for b in disponiveis], format_func=lambda i: f"{bens_map[i]['codigo']} — {bens_map[i]['descricao']}")
                c1, c2 = st.columns(2)
                with c1:
                    retirada = st.date_input("Data de retirada *", value=date.today(), format="DD/MM/YYYY")
                    entrega = st.text_input("Responsável pela entrega *", value=nome_usuario)
                with c2:
                    prevista = st.date_input("Previsão de devolução", value=None, format="DD/MM/YYYY")
                    recebimento = st.text_input("Responsável pelo recebimento *", value=pessoas_map[pessoa_id]["nome"])
                finalidade = st.text_area("Finalidade do empréstimo")
                observacoes = st.text_area("Observações")
                enviar = st.form_submit_button("Registrar empréstimo", type="primary", use_container_width=True)
            if enviar:
                if not ids or not entrega.strip() or not recebimento.strip():
                    st.error("Selecione os bens e informe os responsáveis pela entrega e recebimento.")
                elif prevista and prevista < retirada:
                    st.error("A previsão de devolução não pode ser anterior à retirada.")
                else:
                    try:
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
                        st.session_state["emprestimo_aba_pendente"] = "Emitir recibo"
                        st.session_state["recibo_numero_pendente"] = resultado["numero"]
                        st.rerun()

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
    paginas = ["Painel principal", "Patrimônios", "Empréstimos", "Devoluções", "Documentos assinados", "Histórico por patrimônio", "Relatórios"]
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
elif pagina == "Empréstimos":
    pagina_emprestimos(papel, nome)
elif pagina == "Devoluções":
    pagina_devolucoes(papel, nome)
elif pagina == "Documentos assinados":
    pagina_documentos(papel)
elif pagina == "Histórico por patrimônio":
    pagina_historico_patrimonio()
elif pagina == "Usuários":
    if papel != "admin":
        st.error("Acesso restrito ao administrador.")
        st.stop()
    st.header("Administração de usuários")
    st.info("Módulo em desenvolvimento. Usuários ainda não podem ser criados nesta tela.")
else:
    st.header(pagina)
    st.info("Módulo em desenvolvimento. Nenhum dado será alterado nesta tela.")
