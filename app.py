import streamlit as st
import PyPDF2
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="IA de Carreira - Luana", layout="wide")
st.title("📄 Analisador & Otimizador (Versão Gemini Flash)")

# --- CONFIGURAÇÃO DA IA (GEMINI) ---
# Tenta pegar a chave. Se não conseguir, para tudo.
try:
    chave_gemini = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=chave_gemini)
except Exception as e:
    st.error("❌ Erro grave: Não encontrei a GEMINI_API_KEY nos Secrets.")
    st.stop()

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
        # Se der erro no sheets, apenas avisa no console do servidor, não trava o usuário
        print(f"Erro ao salvar no Sheets: {e}")
        return False

# --- FUNÇÕES ---
def extrair_texto_pdf(arquivo):
    pdf_reader = PyPDF2.PdfReader(arquivo)
    texto = ""
    for page in pdf_reader.pages:
        texto += page.extract_text()
    return texto

def chamar_ia(prompt_sistema, prompt_usuario):
    # Usando o modelo mais recente e estável
    modelo = genai.GenerativeModel('gemini-1.5-flash')
    
    # O Gemini prefere receber o prompt sistema na configuração ou concatenado
    prompt_completo = f"{prompt_sistema}\n\n---\nANÁLISE O SEGUINTE:\n{prompt_usuario}"
    
    # Geração de resposta
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

OPTIMIZATION_INSTRUCTION = "Gere o currículo otimizado para ATS (Fase 2) em formato Markdown limpo."

# --- INTERFACE ---
col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("Seu Currículo (PDF)", type="pdf")
with col2:
    vaga_text = st.text_area("Descrição da Vaga", height=200)

if "analise_feita" not in st.session_state:
    st.session_state.analise_feita = False

# BOTÃO 1
if st.button("🔍 Analisar (Grátis)"):
    if uploaded_file and vaga_text:
        with st.spinner("O Gemini está analisando..."):
            try:
                texto_cv = extrair_texto_pdf(uploaded_file)
                st.session_state.texto_cv = texto_cv
                st.session_state.vaga_original = vaga_text
                
                resultado = chamar_ia(SYSTEM_PROMPT, f"CV: {texto_cv}\nVaga: {vaga_text}")
                
                st.session_state.analise_resultado = resultado
                st.session_state.analise_feita = True
                
                salvar_no_sheets(vaga_text, "N/A", "Analisado Gemini")
                st.toast("Análise feita com sucesso!")
            except Exception as e:
                st.error(f"Erro ao chamar a IA: {e}")

# EXIBIÇÃO E BOTÃO 2
if st.session_state.analise_feita:
    st.markdown("### Resultado:")
    st.write(st.session_state.analise_resultado)
    
    st.markdown("---")
    if st.button("✨ Gerar Currículo Otimizado"):
        with st.spinner("O Gemini está reescrevendo seu CV..."):
            try:
                ctx = f"CV Original: {st.session_state.texto_cv}\nAnálise anterior: {st.session_state.analise_resultado}\nTarefa: {OPTIMIZATION_INSTRUCTION}"
                final = chamar_ia(SYSTEM_PROMPT, ctx)
                st.write(final)
                salvar_no_sheets(st.session_state.vaga_original, "100", "Gerado Gemini")
                st.success("Currículo Otimizado Gerado!")
            except Exception as e:
                st.error(f"Erro na geração final: {e}")
