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
    page_title="Análise de Currículo - Luana",
    layout="wide"
)

# ---------------- CSS (VISUAL DARK MODE) ----------------
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
st.title("🚀 Analisador & Otimizador de Currículos")
st.caption("Inteligência Artificial para alinhar seu perfil às vagas do mercado.")

st.markdown("""
<div class="info-box">
    <h3>Como funciona?</h3>
    <p>
        Esta ferramenta lê seu PDF e a descrição da vaga para simular a análise de um recrutador.
        Você receberá uma nota de compatibilidade, pontos de atenção e poderá gerar uma nova versão do currículo otimizada para passar nos filtros (ATS).
    </p>
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
    # Procura por "Nota: 90%" ou "Nota: 90" no texto
    match = re.search(r'(?:Nota|Minha Nota):?\s*\*?(\d+)', texto, re.IGNORECASE)
    return int(match.group(1)) if match else 0

def salvar_no_sheets(email, nota, vaga, cv_original, analise, cv_otimizado=""):
    """
    Salva o histórico completo no Google Sheets.
    Ordem: Data | Email | Nota | Vaga | CV Original | Análise | CV Otimizado
    """
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes
        )
        gc = gspread.authorize(creds)
        sh = gc.open("Banco de Curriculos")
        sheet = sh.sheet1

        # Dados completos para treino futuro da IA
        dados = [
            str(datetime.now()),     # Data
            email,                   # Email
            f"{nota}%",              # Nota formatada
            vaga,                    # Texto completo da vaga
            cv_original,             # Texto completo do CV antigo
            analise,                 # O feedback da IA
            cv_otimizado             # O novo CV (vazio na primeira etapa)
        ]

        sheet.append_row(dados)
        return True
    except Exception as e:
        print(f"ERRO PLANILHA: {e}")
        return str(e)

def chamar_ia(prompt_sistema, dados):
    # --- MUDANÇA ESTRATÉGICA: Usando o ALIAS 'latest' ---
    # Isso pega a versão mais estável disponível para sua conta, evitando erro de cota
    model = genai.GenerativeModel("gemini-flash-latest")
    
    prompt = f"{prompt_sistema}\n\n---\nDADOS:\n{dados}"
    return model.generate_content(prompt).text

# ---------------- PROMPTS ----------------
SYSTEM_PROMPT = """
Você é um Especialista em Carreiras e Recrutamento Tech.
Analise o currículo e a vaga.
Saída obrigatória (Markdown):
1. **Pontos Fortes:** (O que conecta com a vaga)
2. **Gaps/Atenção:** (O que falta ou está fraco)
3. **Minha Nota:** X% (Apenas o número de 0 a 100)
4. **Veredito:** (Sugestão de ação)
"""

OPTIMIZATION_PROMPT = """
Atue como um redator de currículos especialista em ATS (Applicant Tracking Systems).
Reescreva o currículo fornecido para maximizar a aderência à vaga, usando as palavras-chave encontradas.
Mantenha a verdade, mas melhore a apresentação, verbos de ação e foco em resultados.
Saída: Apenas o texto do novo currículo em Markdown.
"""

# ---------------- FORMULÁRIO ----------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Seus Dados")
    email = st.text_input("E-mail para contato")
    pdf = st.file_uploader("Currículo (PDF)", type="pdf")

with col2:
    st.subheader("2. A Vaga")
    vaga = st.text_area("Descrição da Vaga", height=260, placeholder="Cole aqui os requisitos...")

st.markdown("---")
aceite = st.checkbox("Concordo em compartilhar os dados para análise e aprimoramento da ferramenta.")

# ---------------- ESTADO ----------------
if "resultado" not in st.session_state:
    st.session_state.resultado = None

# ---------------- BOTÃO 1: ANALISAR ----------------
if st.button("🔍 Analisar Compatibilidade"):
    if not aceite:
        st.warning("⚠️ Você precisa aceitar o compartilhamento de dados para usar a ferramenta.")
    elif not email or not pdf or not vaga:
        st.warning("⚠️ Preencha e-mail, currículo e vaga.")
    else:
        with st.spinner("Lendo currículo e comparando com a vaga..."):
            try:
                texto_cv = extrair_texto_pdf(pdf)
                
                # Chama a IA
                resposta = chamar_ia(SYSTEM_PROMPT, f"CV: {texto_cv}\nVaga: {vaga}")
                
                # Guarda na memória do app
                st.session_state.resultado = resposta
                st.session_state.texto_cv = texto_cv
                st.session_state.vaga = vaga
                st.session_state.email = email
                
                # Extrai nota e salva a primeira etapa
                nota = extrair_nota(resposta)
                salvou = salvar_no_sheets(email, nota, vaga, texto_cv, resposta, "")
                
                if salvou == True:
                    st.toast("Análise salva com sucesso!")
                else:
                    st.error(f"Erro ao salvar na planilha: {salvou}")
                    
            except Exception as e:
                st.error(f"Erro técnico na IA: {e}")

# ---------------- RESULTADOS E BOTÃO 2 ----------------
if st.session_state.resultado:
    st.markdown("---")
    st.subheader("📊 Resultado da Análise")
    
    nota = extrair_nota(st.session_state.resultado)
    st.progress(nota / 100)
    st.caption(f"Compatibilidade: {nota}%")
    
    # Gráfico
    dados_grafico = pd.DataFrame({
        "Critério": ["Experiência", "Palavras-Chave", "Formatação", "Geral"],
        "Nota": [max(nota-5, 0), nota, max(nota-10, 0), nota]
    })
    st.bar_chart(dados_grafico.set_index("Critério"))

    st.write(st.session_state.resultado)
    
    st.markdown("---")
    if st.button("✨ Gerar Currículo Otimizado (Versão ATS)"):
        with st.spinner("Reescrevendo seu currículo..."):
            try:
                # Chama a IA para a segunda tarefa
                novo_cv = chamar_ia(
                    OPTIMIZATION_PROMPT, 
                    f"CV ORIGINAL:\n{st.session_state.texto_cv}\n\nANÁLISE ANTERIOR:\n{st.session_state.resultado}"
                )
                
                st.markdown("### 📝 Novo Currículo Sugerido")
                st.code(novo_cv, language="markdown") # Mostra em caixa de código para fácil cópia
                
                # Salva a segunda etapa (agora preenchendo a coluna final)
                salvar_no_sheets(
                    st.session_state.email, 
                    100, 
                    st.session_state.vaga, 
                    st.session_state.texto_cv, 
                    st.session_state.resultado, 
                    novo_cv
                )
                
                st.success("Currículo gerado e salvo no banco de dados!")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao gerar currículo: {e}")
