import streamlit as st
import PyPDF2
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="IA de Carreira - Luana", layout="wide")
st.title("📄 Analisador & Otimizador (Modo Diagnóstico)")

# --- CONFIGURAÇÃO DA IA ---
try:
    chave_gemini = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=chave_gemini)
except Exception as e:
    st.error(f"Erro na configuração da chave: {e}")

# --- BARRA LATERAL DE DIAGNÓSTICO ---
with st.sidebar:
    st.header("Área Técnica")
    if st.button("🆘 Diagnóstico de Modelos"):
        st.write("Consultando o Google...")
        try:
            # Pede pro Google listar o que está disponível pra essa chave
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    st.code(m.name) # Mostra o nome exato
        except Exception as e:
            st.error(f"Erro ao listar: {e}")

# --- FUNÇÕES ---
def extrair_texto_pdf(arquivo):
    pdf_reader = PyPDF2.PdfReader(arquivo)
    texto = ""
    for page in pdf_reader.pages:
        texto += page.extract_text()
    return texto

def chamar_ia(prompt_sistema, prompt_usuario):
    # --- TENTATIVA COM NOME GENÉRICO ---
    # Se o diagnóstico mostrar outro nome, vamos mudar esta linha depois:
    modelo = genai.GenerativeModel('gemini-1.5-flash') 
    
    prompt_completo = f"{prompt_sistema}\n\n---\nDADOS:\n{prompt_usuario}"
    response = modelo.generate_content(prompt_completo)
    return response.text

# --- CONEXÃO SHEETS ---
def salvar_no_sheets(vaga, nota, status):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        gc = gspread.authorize(credentials)
        sh = gc.open("Banco de Curriculos") 
        worksheet = sh.sheet1
        dados = [str(datetime.now()), vaga[:50], status, nota]
        worksheet.append_row(dados)
        return True
    except Exception as e:
        print(f"Erro sheets: {e}")
        return False

# --- PROMPTS ---
SYSTEM_PROMPT = """
Você é um Parceiro de Carreira. Analise o currículo e a vaga.
Retorne APENAS a Fase 1: Aderência, Atenção, Nota (0-100), Sugestão.
"""

# --- INTERFACE ---
col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("Seu Currículo (PDF)", type="pdf")
with col2:
    vaga_text = st.text_area("Descrição da Vaga", height=200)

if "analise_feita" not in st.session_state:
    st.session_state.analise_feita = False

if st.button("🔍 Analisar"):
    if uploaded_file and vaga_text:
        with st.spinner("Analisando..."):
            try:
                texto_cv = extrair_texto_pdf(uploaded_file)
                st.session_state.texto_cv = texto_cv
                st.session_state.vaga_original = vaga_text
                
                resultado = chamar_ia(SYSTEM_PROMPT, f"CV: {texto_cv}\nVaga: {vaga_text}")
                st.session_state.analise_resultado = resultado
                st.session_state.analise_feita = True
                
                salvar_no_sheets(vaga_text, "N/A", "Analisado")
            except Exception as e:
                st.error(f"Erro na IA: {e}")

if st.session_state.analise_feita:
    st.write(st.session_state.analise_resultado)
