import streamlit as st
import PyPDF2
import google.generativeai as genai
import gspread
import re
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CV Optimizer - Luana", layout="wide")

# --- CSS (Visual Dark Mode Aprimorado) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3 { color: #FAFAFA !important; font-family: 'Helvetica Neue', sans-serif; }
    
    /* Estilo para a caixa de explicação */
    .info-box {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #7C3AED;
        margin-bottom: 20px;
    }
    
    /* Inputs */
    .stTextInput input, .stTextArea textarea { 
        background-color: #262730 !important; 
        color: #FFFFFF !important; 
        border: 1px solid #4A4A4A; 
    }
    [data-testid="stFileUploader"] { background-color: #262730; border: 1px dashed #7C3AED; }
    
    /* Botão */
    .stButton > button { 
        background-color: #7C3AED; 
        color: white !important; 
        width: 100%;
        font-size: 18px;
        padding: 0.8rem;
        border-radius: 8px; 
        border: none; 
        font-weight: bold; 
    }
    .stButton > button:hover { background-color: #6D28D9; }
</style>
""", unsafe_allow_html=True)

# --- HEADER E DESCRIÇÃO DO PROJETO ---
st.title("🚀 CV Optimizer: Sua IA de Carreira")

st.markdown("""
<div class="info-box">
    <h3>O que é este projeto?</h3>
    <p>Esta é uma ferramenta experimental desenvolvida para ajudar candidatos a alinharem seus currículos com as vagas desejadas usando Inteligência Artificial.</p>
    <p><b>Como funciona:</b> Nossa IA lê seu PDF, lê a vaga e atua como um recrutador sênior, te dando dicas de ouro e reescrevendo pontos estratégicos para passar nos filtros automáticos (ATS).</p>
</div>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÃO DA IA ---
try:
    chave_gemini = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=chave_gemini)
except Exception as e:
    st.error("Erro na chave do Gemini. Verifique os Secrets.")
    st.stop()

# --- FUNÇÕES ---
def extrair_nota_do_texto(texto_ia):
    match = re.search(r'Nota:?\s*\*?(\d+)', texto_ia, re.IGNORECASE)
    if match:
        return match.group(1) + "%"
    return "N/A"

def extrair_texto_pdf(arquivo):
    pdf_reader = PyPDF2.PdfReader(arquivo)
    texto = ""
    for page in pdf_reader.pages:
        texto += page.extract_text()
    return texto

def salvar_no_sheets(email, vaga, nota, status):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        gc = gspread.authorize(credentials)
        sh = gc.open("Banco de Curriculos") 
        worksheet = sh.sheet1
        
        # Ordem das colunas: Data | Email | Vaga | Status | Nota
        dados = [str(datetime.now()), email, vaga, status, nota]
        
        worksheet.append_row(dados)
        return True
    except Exception as e:
        print(f"Erro ao salvar no Sheets: {e}")
        return False

def chamar_ia(prompt_sistema, prompt_usuario):
    modelo = genai.GenerativeModel('gemini-2.5-flash')
    prompt_completo = f"{prompt_sistema}\n\n---\nDADOS PARA ANÁLISE:\n{prompt_usuario}"
    response = modelo.generate_content(prompt_completo)
    return response.text

# --- PROMPTS ---
SYSTEM_PROMPT = """
Você é um Parceiro de Carreira e Recrutador Sênior. 
Analise o currículo e a vaga. Retorne APENAS a Fase 1:
1. Pontos de Aderência (Match).
2. Pontos de Atenção (Gaps).
3. Minha Nota: 0 a 100% (Sempre coloque "Minha Nota: X%" numa linha separada).
4. Minha Sugestão Sincera.
5. Pergunta final: "Quer gerar o otimizado?"
"""

OPTIMIZATION_INSTRUCTION = """
O usuário disse SIM. Gere a FASE 2: Currículo Otimizado para ATS.
Integre palavras-chave, use verbos fortes e formatação Markdown limpa.
"""

# --- FORMULÁRIO DE DADOS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Seus Dados")
    email_usuario = st.text_input("Seu melhor e-mail", placeholder="exemplo@email.com")
    uploaded_file = st.file_uploader("Seu Currículo (PDF)", type="pdf")

with col2:
    st.subheader("2. A Vaga")
    vaga_text = st.text_area("Cole a descrição da vaga aqui", height=280, placeholder="Requisitos, responsabilidades...")

# --- OPT-IN E AÇÃO ---
st.markdown("---")
termo_aceite = st.checkbox("Concordo em compartilhar meus dados para fins de aprimoramento da ferramenta e contato futuro sobre carreira.")

if "analise_feita" not in st.session_state:
    st.session_state.analise_feita = False

# BOTÃO DE AÇÃO PRINCIPAL
if st.button("🔍 Analisar Compatibilidade"):
    if not termo_aceite:
        st.warning("⚠️ Para usar a ferramenta, você precisa concordar com o compartilhamento de dados acima.")
    elif not email_usuario or not uploaded_file or not vaga_text:
        st.warning("⚠️ Por favor, preencha o e-mail, anexe o currículo e a vaga.")
    else:
        with st.spinner("Nossa IA está lendo seu perfil..."):
            try:
                texto_cv = extrair_texto_pdf(uploaded_file)
                st.session_state.texto_cv = texto_cv
                st.session_state.vaga_original = vaga_text
                st.session_state.email = email_usuario # Guarda o email na sessão
                
                resultado = chamar_ia(SYSTEM_PROMPT, f"CV: {texto_cv}\nVaga: {vaga_text}")
                st.session_state.analise_resultado = resultado
                st.session_state.analise_feita = True
                
                nota_real = extrair_nota_do_texto(resultado)
                salvar_no_sheets(email_usuario, vaga_text, nota_real, "Analisado - Fase 1")
                
                st.toast("Análise concluída!")
            except Exception as e:
                st.error(f"Erro técnico: {e}")

# --- RESULTADOS ---
if st.session_state.analise_feita:
    st.markdown("---")
    st.subheader("💬 Feedback do Recrutador IA")
    st.write(st.session_state.analise_resultado)
    
    st.markdown("---")
    if st.button("✨ Gerar Currículo Otimizado ATS"):
        with st.spinner("Reescrevendo seu currículo..."):
            try:
                ctx = f"CV Original: {st.session_state.texto_cv}\nAnálise: {st.session_state.analise_resultado}\nTarefa: {OPTIMIZATION_INSTRUCTION}"
                final = chamar_ia(SYSTEM_PROMPT, ctx)
                st.write(final)
                
                # Salva a segunda etapa com o email que está na memória
                salvar_no_sheets(st.session_state.email, st.session_state.vaga_original, "100%", "Gerado CV Novo")
                st.success("Currículo Gerado com Sucesso!")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao gerar: {e}")
