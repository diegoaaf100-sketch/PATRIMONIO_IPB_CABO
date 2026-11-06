# Sistema de Gestão Patrimonial IPB - CABO

Primeira versão: login via Supabase Auth, checagem de perfil ativo e painel Streamlit.

## Preparação

1. Instale Python 3.11+.
2. Instale as dependências: `pip install -r requirements.txt`.
3. Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`.
4. Preencha `SUPABASE_URL` e `SUPABASE_ANON_KEY` (chave pública). **Nunca utilize a service_role key**.
5. Execute `streamlit run app.py`.

## Publicação

No Streamlit Community Cloud, selecione o repositório e o arquivo `app.py`. Configure as duas variáveis em **Advanced settings > Secrets**, sem colocar o arquivo `secrets.toml` no GitHub.

## Limitações desta versão

- As telas de patrimônios, empréstimos, devoluções, relatórios e usuários são apenas espaços reservados.
- Antes de usar em produção, revisar políticas RLS, privilégios das funções SECURITY DEFINER, auditoria, consistência de empréstimos e políticas do Storage.
- Para criação de usuários por administrador, será necessário um serviço seguro no servidor, sem expor a chave administrativa ao navegador.
