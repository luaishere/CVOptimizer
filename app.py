import streamlit as st
import PyPDF2
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="IA de Carreira - Luana", layout="wide")
st.title("📄 Analisador & Otimizador (Versão Gemini)")

# --- CONFIGURAÇÃO DA IA (GEMINI) ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("Erro na chave do Gemini. Verifique os Secrets.")

# --- CONEXÃO COM GOOGLE SHEETS ---
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
        # Se der erro no sheets, não para o app, só avisa
        print(f"Erro sheets: {e}")
        return False

# --- FUNÇÕES ---
def extrair_texto_pdf(arquivo):
    pdf_reader = PyPDF2.PdfReader(arquivo)
    texto = ""
    for page in pdf_reader.pages:
        texto += page.extract_text()
    return texto

def chamar_ia(prompt_sistema, prompt_usuario):
    # O Gemini junta sistema e usuario de forma diferente, mas vamos simplificar
    modelo = genai.GenerativeModel('gemini-1.5-flash') # Modelo rápido e grátis
    
    prompt_completo = f"{prompt_sistema}\n\n---\nDADOS DO USUÁRIO:\n{prompt_usuario}"
    
    response = modelo.generate_content(prompt_completo)
    return response.text

# --- PROMPT ---
SYSTEM_PROMPT = """
Você é um Parceiro de Carreira e Recrutador Sênior. 
Analise o currículo e a vaga. Retorne APENAS a Fase 1:
1. Pontos de Aderência.
2. Pontos de Atenção.
3. Minha Nota: (0 a 100).
4. Sugestão Sincera.
5. Pergunta final: "Quer gerar o otimizado?"
"""

OPTIMIZATION_INSTRUCTION = "Gere o currículo otimizado para ATS (Fase 2)."

# --- INTERFACE ---
col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("Seu Currículo (PDF)", type="pdf")
with col2:
    vaga_text = st.text_area("Descrição da Vaga", height=200)

if "analise_feita" not in st.session_state:
    st.session_state.analise_feita = False

if st.button("🔍 Analisar (Grátis)"):
    if uploaded_file and vaga_text:
        with st.spinner("O Gemini está analisando..."):
            texto_cv = extrair_texto_pdf(uploaded_file)
            st.session_state.texto_cv = texto_cv
            st.session_state.vaga_original = vaga_text
            
            resultado = chamar_ia(SYSTEM_PROMPT, f"CV: {texto_cv}\nVaga: {vaga_text}")
            
            st.session_state.analise_resultado = resultado
            st.session_state.analise_feita = True
            
            salvar_no_sheets(vaga_text, "N/A", "Analisado Gemini")
            st.toast("Análise feita!")

if st.session_state.analise_feita:
    st.write(st.session_state.analise_resultado)
    
    if st.button("✨ Gerar Currículo Otimizado"):
        with st.spinner("O Gemini está escrevendo..."):
            ctx = f"CV Original: {st.session_state.texto_cv}\nAnálise anterior: {st.session_state.analise_resultado}\nTarefa: {OPTIMIZATION_INSTRUCTION}"
            final = chamar_ia(SYSTEM_PROMPT, ctx)
            st.write(final)
            salvar_no_sheets(st.session_state.vaga_original, "100", "Gerado Gemini")
            st.success("Pronto!")
