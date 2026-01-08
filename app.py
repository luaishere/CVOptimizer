import streamlit as st
import PyPDF2
import google.generativeai as genai
import gspread
import re
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime

# ---------------- CONFIGURAÇÃO DA PÁGINA ----------------
st.set_page_config(
    page_title="Análise de Currículo",
    layout="wide"
)

# ---------------- CSS (VISUAL) ----------------
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3 { color: #FAFAFA !important; font-family: 'Helvetica Neue', sans-serif; }

    .info-box {
        background-color: #1F2937;
        padding: 24px;
        border-radius: 12px;
        border-left: 5px solid #7C3AED;
        margin-bottom: 24px;
    }

    .stTextInput input, .stTextArea textarea { 
        background-color: #1F2937 !important; 
        color: #FFFFFF !important; 
        border: 1px solid #374151; 
    }

    [data-testid="stFileUploader"] {
        background-color: #1F2937;
        border: 1px dashed #7C3AED;
        padding: 10px;
        border-radius: 8px;
    }

    .stButton > button { 
        background-color: #7C3AED; 
        color: white !important; 
        width: 100%;
        font-size: 17px;
        padding: 0.9rem;
        border-radius: 10px; 
        border: none; 
        font-weight: 600; 
    }

    .stButton > button:hover { background-color: #6D28D9; }
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.title("Seu currículo está mesmo pronto para essa vaga?")
st.caption("Receba um feedback claro, honesto e sugestões práticas para melhorar suas chances.")

st.markdown("""
<div class="info-box">
    <h3>Como funciona?</h3>
    <p>
        Você envia seu currículo em PDF e cola a descrição da vaga que deseja.
        A ferramenta analisa os dois juntos e mostra:
    </p>
    <ul>
        <li>O que já está forte no seu currículo</li>
        <li>O que pode estar te atrapalhando</li>
        <li>Uma nota geral de compatibilidade</li>
        <li>Sugestões diretas de melhoria</li>
    </ul>
    <p>Se quiser, você pode gerar uma versão do currículo mais alinhada à vaga.</p>
</div>
""", unsafe_allow_html=True)

# ---------------- IA ----------------
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error(f"Erro ao carregar a chave da IA: {e}")
    st.stop()

# ---------------- FUNÇÕES ----------------
def extrair_texto_pdf(arquivo):
    reader = PyPDF2.PdfReader(arquivo)
    texto = ""
    for page in reader.pages:
        texto += page.extract_text()
    return texto

def extrair_nota(texto):
    # Tenta achar "Minha Nota: X%" ou variações
    match = re.search(r'(?:Nota|Minha Nota):?\s*\*?(\d+)', texto, re.IGNORECASE)
    return int(match.group(1)) if match else 0

def salvar_no_sheets(email, nota, vaga, cv_original, analise, cv_otimizado=""):
    """
    Salva TUDO: Dados do usuário, textos completos e resultados.
    Ordem das Colunas: Data | Email | Nota | Vaga | CV Original | Análise | CV Otimizado
    """
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes
        )
        gc = gspread.authorize(creds)
        
        # Abre a planilha (certifique-se que o nome é exato)
        sh = gc.open("Banco de Curriculos")
        sheet = sh.sheet1

        # Prepara a linha de dados
        dados_para_salvar = [
            str(datetime.now()),     # Data
            email,                   # Email
            f"{nota}%",              # Nota
            vaga,                    # Vaga COMPLETA (sem cortes)
            cv_original,             # Texto do CV Original (O "Antes")
            analise,                 # O que a IA pensou
            cv_otimizado             # O CV Novo (O "Depois") - pode vir vazio na 1ª etapa
        ]
        
        sheet.append_row(dados_para_salvar)
        return True
        
    except Exception as e:
        # Imprime o erro no console do servidor para você ver o que houve
        print(f"ERRO CRÍTICO AO SALVAR: {e}")
        return str(e) # Retorna o erro para exibir na tela se precisar

def chamar_ia(prompt_sistema, dados):
    # Usando o modelo com mais limite gratuito
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"{prompt_sistema}\n\n---\n{dados}"
    return model.generate_content(prompt).text

# ---------------- PROMPTS ----------------
SYSTEM_PROMPT = """
Analise o currículo e a vaga informada.
Retorne APENAS nesta estrutura:
1. Pontos fortes do currículo
2. Pontos de atenção
3. Minha Nota: X%
4. Sugestão direta e sincera
Finalize perguntando se deseja gerar uma versão melhorada do currículo.
"""

OPTIMIZATION_PROMPT = """
Gere uma versão de currículo clara, organizada e objetiva.
Use linguagem simples, bullets curtos e destaque resultados.
"""

# ---------------- FORMULÁRIO ----------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Sobre você")
    email = st.text_input("Seu e-mail")
    pdf = st.file_uploader("Seu currículo em PDF", type="pdf")

with col2:
    st.subheader("2. Sobre a vaga que você quer")
    vaga = st.text_area("Cole aqui a descrição da vaga", height=260)

st.markdown("---")
aceite = st.checkbox(
    "Concordo em compartilhar meus dados para aprimorar a ferramenta e receber conteúdos sobre carreira."
)

# ---------------- ESTADO ----------------
if "resultado" not in st.session_state:
    st.session_state.resultado = None

# ---------------- AÇÃO ----------------
if st.button("Ver como meu currículo se sai nessa vaga"):
    if not aceite or not email or not pdf or not vaga:
        st.warning("Preencha todas as informações para continuar.")
    else:
        with st.spinner("Analisando seu currículo..."):
            try:
                texto_cv = extrair_texto_pdf(pdf)
                
                # Chamada para a IA
                resposta = chamar_ia(
                    SYSTEM_PROMPT,
                    f"CURRÍCULO:\n{texto_cv}\n\nVAGA:\n{vaga}"
                )
                
                # Salvar na sessão
                st.session_state.resultado = resposta
                st.session_state.texto_cv = texto_cv
                st.session_state.vaga = vaga
                st.session_state.email = email
                
                # Extrair nota
                nota = extrair_nota(resposta)
                
                # Tenta salvar
                salvou = salvar_no_sheets(email, nota, vaga, texto_cv, resposta, "")
                
                if salvou != True:
                    st.error(f"Atenção: A análise foi feita, mas deu erro ao salvar no banco: {salvou}")
                
            except Exception as e:
                st.error(f"Ocorreu um erro técnico: {e}")

# ---------------- RESULTADO ----------------
if st.session_state.resultado:
    st.markdown("---")
    st.subheader("📊 Resultado da análise")

    nota = extrair_nota(st.session_state.resultado)
    
    # Barra de progresso visual
    st.progress(nota / 100)
    st.caption(f"{nota}% de compatibilidade com a vaga")

    # Gráfico simples
    dados = pd.DataFrame({
        "Aspecto": ["Experiência", "Habilidades", "Clareza", "Aderência à vaga"],
        "Pontuação": [
            max(nota - 10, 0),
            nota,
            max(nota - 5, 0),
            nota
        ]
    })
    st.bar_chart(dados.set_index("Aspecto"))

    st.markdown("### 💬 Feedback detalhado")
    st.write(st.session_state.resultado)

    st.markdown("---")
    if st.button("Gerar versão melhorada do meu currículo"):
        with st.spinner("Gerando currículo otimizado..."):
            try:
                novo_cv = chamar_ia(
                    OPTIMIZATION_PROMPT,
                    f"{st.session_state.texto_cv}\n\n{st.session_state.resultado}"
                )
                st.markdown("### ✨ Currículo sugerido")
                st.write(novo_cv)

                # Salva novamente, agora COM o currículo novo preenchido
                salvar_no_sheets(
                    st.session_state.email,
                    100, # Nota simbólica de conclusão
                    st.session_state.vaga,
                    st.session_state.texto_cv,
                    st.session_state.resultado,
                    novo_cv # <--- AQUI VAI O CURRÍCULO NOVO
                )

                st.success("Currículo gerado e salvo com sucesso!")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao gerar: {e}")
