import streamlit as st
import PyPDF2
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="IA de Carreira - Luana", layout="wide")

# --- CSS PARA DEIXAR BONITO (Opcional, mas já dá um visual) ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    h1 { color: #2c3e50; }
    .stButton>button { background-color: #4CAF50; color: white; border-radius: 8px; width: 100%; }
</style>
""", unsafe_allow_html=True)

st.title("🚀 Analisador & Otimizador de Currículos")
st.markdown("Cole a vaga, suba o PDF e deixe a IA alinhar seu perfil.")

# --- CONFIGURAÇÃO DA IA (GEMINI) ---
try:
    chave_gemini = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=chave_gemini)
except Exception as e:
    st.error("Erro na chave do Gemini. Verifique os Secrets.")
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
    # --- MODELO CORRIGIDO BASEADO NO SEU DIAGNÓSTICO ---
    modelo = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt_completo = f"{prompt_sistema}\n\n---\nDADOS PARA ANÁLISE:\n{prompt_usuario}"
    response = modelo.generate_content(prompt_completo)
    return response.text

# --- SEU PROMPT MESTRE ORIGINAL ---
SYSTEM_PROMPT = """
Você é um Parceiro de Carreira e Recrutador Sênior. 
Sua prioridade é ser empático, claro e direto (sem "robobês").
Você nunca inventa dados que não existam no currículo.

ESTRUTURA DA FASE 1 (ANÁLISE):
Analise o currículo e a vaga fornecidos. Retorne APENAS a Fase 1:
1. Pontos de Aderência (O que deu "match"): Cite experiências específicas.
2. Pontos de Atenção (Onde o sapato aperta): Seja sincero sobre gaps.
3. Minha Nota: 0 a 100% (Baseada em percepção técnica).
4. Minha Sugestão Sincera: Aplicar? Cautela? Não é o momento?
5. A Pergunta: "Dito isso, quer que eu faça a mágica e gere a versão otimizada para ATS mesmo assim?"

IMPORTANTE: Considere o tempo de casa e não seja genérico.
"""

OPTIMIZATION_INSTRUCTION = """
O usuário respondeu "SIM". Agora execute a FASE 2:
Gere o currículo focado em passar no ATS.
- Integre palavras-chave da vaga naturalmente.
- Resumo Profissional focado na senioridade da vaga.
- Experiência com verbos fortes (Liderou, Criou, Estruturou) e resultados no topo.
- Formatação limpa (Markdown), pronta para copiar.
"""

# --- INTERFACE ---
col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("📂 Seu Currículo (PDF)", type="pdf")
with col2:
    vaga_text = st.text_area("📋 Descrição da Vaga", height=200)

if "analise_feita" not in st.session_state:
    st.session_state.analise_feita = False

# BOTÃO 1: ANALISAR
if st.button("🔍 Analisar Aderência"):
    if uploaded_file and vaga_text:
        with st.spinner("Lendo currículo e comparando com a vaga..."):
            try:
                texto_cv = extrair_texto_pdf(uploaded_file)
                st.session_state.texto_cv = texto_cv
                st.session_state.vaga_original = vaga_text
                
                resultado = chamar_ia(SYSTEM_PROMPT, f"CV: {texto_cv}\nVaga: {vaga_text}")
                
                st.session_state.analise_resultado = resultado
                st.session_state.analise_feita = True
                
                salvar_no_sheets(vaga_text, "N/A", "Analisado - Fase 1")
                st.toast("Análise concluída e salva!")
            except Exception as e:
                st.error(f"Erro na IA: {e}")
    else:
        st.warning("Por favor, anexe o currículo e a descrição da vaga.")

# EXIBIÇÃO E BOTÃO 2
if st.session_state.analise_feita:
    st.markdown("---")
    st.subheader("💬 Feedback do Parceiro")
    st.write(st.session_state.analise_resultado)
    
    st.markdown("---")
    st.info("Gostou da análise? Quer gerar o documento final?")
    
    if st.button("✨ Gerar Currículo Otimizado ATS"):
        with st.spinner("Reescrevendo seu
