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
    page_title="Currículo vs Vaga - Luana",
    page_icon="🎯",
    layout="wide"
)

# ---------------- CSS (VISUAL AMIGÁVEL & MODERNO) ----------------
st.markdown("""
<style>
    /* Fundo Escuro Confortável */
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    
    /* Títulos com destaque */
    h1 { color: #A78BFA !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }
    h2, h3 { color: #F3F4F6 !important; }
    
    /* Caixa de Explicação (Hero Section) */
    .hero-box {
        background: linear-gradient(90deg, #1F2937 0%, #111827 100%);
        padding: 30px;
        border-radius: 15px;
        border-left: 6px solid #8B5CF6; /* Roxo suave */
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .hero-box h3 { color: #C4B5FD !important; margin-top: 0; }
    .hero-box p { font-size: 1.1rem; line-height: 1.6; }

    /* Campos de Entrada */
    .stTextInput input, .stTextArea textarea { 
        background-color: #1F2937 !important; 
        color: #FFFFFF !important; 
        border: 1px solid #374151; 
        border-radius: 8px;
    }
    
    /* Upload */
    [data-testid="stFileUploader"] {
        background-color: #1F2937;
        border: 2px dashed #6D28D9;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
    }

    /* Botões Principais */
    .stButton > button { 
        background: linear-gradient(90deg, #7C3AED 0%, #6D28D9 100%);
        color: white !important; 
        width: 100%;
        font-size: 18px;
        padding: 1rem;
        border-radius: 12px; 
        border: none; 
        font-weight: 700; 
        box-shadow: 0 4px 14px 0 rgba(124, 58, 237, 0.39);
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover { 
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(124, 58, 237, 0.23);
    }
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER & COPYWRITING ----------------
st.title("🎯 Seu Currículo passa no filtro?")
st.caption("Ferramenta gratuita para profissionais em busca de recolocação.")

st.markdown("""
<div class="hero-box">
    <h3>Não deixe um robô eliminar sua chance</h3>
    <p>
        Hoje em dia, a maioria das empresas usa sistemas automáticos (IA) para ler currículos antes mesmo de um humano ver. 
        Se as palavras certas não estiverem lá, você é reprovado automaticamente.
    </p>
    <p>
        <b>Como te ajudamos:</b>
        <br>1. Nossa IA lê seu currículo e a vaga como se fosse o recrutador.
        <br>2. Te mostramos exatamente o que está faltando.
        <br>3. Criamos uma nova versão do seu currículo ajustada para passar nessa vaga específica.
    </p>
</div>
""", unsafe_allow_html=True)

# ---------------- CONFIGURAÇÃO TÉCNICA ----------------
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error(f"Erro de conexão. Avise o administrador.")
    st.stop()

# ---------------- FUNÇÕES DE BACKEND ----------------
def extrair_texto_pdf(arquivo):
    reader = PyPDF2.PdfReader(arquivo)
    texto = ""
    for page in reader.pages:
        texto += page.extract_text()
    return texto

def extrair_nota(texto):
    match = re.search(r'(?:Nota|Minha Nota):?\s*\*?(\d+)', texto, re.IGNORECASE)
    return int(match.group(1)) if match else 0

def salvar_no_sheets(email, nota, vaga, cv_original, analise, cv_otimizado=""):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes
        )
        gc = gspread.authorize(creds)
        sh = gc.open("Banco de Curriculos")
        sheet = sh.sheet1

        dados = [
            str(datetime.now()),
            email,
            f"{nota}%",
            vaga,
            cv_original,
            analise,
            cv_otimizado
        ]
        sheet.append_row(dados)
        return True
    except Exception as e:
        print(f"Erro ao salvar: {e}")
        return False

def chamar_ia(prompt_sistema, dados):
    # Usando o modelo 'latest' para evitar erros de limite
    model = genai.GenerativeModel("gemini-flash-latest")
    prompt = f"{prompt_sistema}\n\n---\nINFORMAÇÕES:\n{dados}"
    return model.generate_content(prompt).text

# ---------------- PROMPTS (PERSONALIDADE DA IA) ----------------
# Aqui definimos o tom de voz da IA: Empática, Mentora, Encorajadora.
SYSTEM_PROMPT = """
Você é uma Mentora de Carreira experiente e empática, especializada em recolocação profissional.
Seu objetivo é ajudar candidatos (júniors ou em transição) a passarem pelos filtros de IA dos recrutadores.

Analise o currículo e a vaga. Fale diretamente com o candidato (use "você").
Estrutura da resposta (use Markdown):

1. **Onde você brilha ✨:** (Liste o que está ótimo e conecta com a vaga)
2. **Cuidado com isso ⚠️:** (O que falta, gaps de palavras-chave ou erros que podem reprovar no sistema. Seja gentil mas honesta)
3. **Minha Nota:** X% (Apenas o número de 0 a 100)
4. **Veredito da Mentora:** (Vale a pena aplicar? O que precisa mudar urgente?)

Seja clara, evite jargões complexos de RH sem explicar.
"""

OPTIMIZATION_PROMPT = """
Atue como uma Especialista em Currículos para Sistemas ATS.
Sua missão: Reescrever o currículo do candidato para aumentar a chance de entrevista nesta vaga específica.

Regras:
- Mantenha a veracidade (não invente experiências), mas mude a forma de escrever.
- Use as palavras-chave exatas da descrição da vaga.
- Use verbos de ação fortes (Liderei, Criei, Organizei).
- Foco em resultados.
- Adicione um breve Resumo Profissional no topo alinhado à vaga.

Saída: Apenas o texto do currículo formatado, pronto para copiar.
"""

# ---------------- FORMULÁRIO ----------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Quem é você?")
    email = st.text_input("Seu melhor e-mail", placeholder="ex: joao@gmail.com")
    pdf = st.file_uploader("Seu Currículo (PDF)", type="pdf", help="Pode ser o currículo que você já usa.")

with col2:
    st.subheader("2. Qual a vaga dos sonhos?")
    vaga = st.text_area("Descrição da Vaga", height=260, placeholder="Cole aqui tudo que estava escrito no anúncio da vaga (Requisitos, Responsabilidades, etc)...")

st.markdown("---")
aceite = st.checkbox("Aceito compartilhar meus dados para gerar a análise e receber dicas de carreira futuramente.")

# ---------------- ESTADO ----------------
if "resultado" not in st.session_state:
    st.session_state.resultado = None

# ---------------- BOTÃO 1 ----------------
if st.button("🚀 Descobrir minhas chances"):
    if not aceite:
        st.warning("⚠️ Precisamos do seu aceite para prosseguir.")
    elif not email or not pdf or not vaga:
        st.warning("⚠️ Opa, faltou preencher alguma coisa acima!")
    else:
        with st.spinner("Lendo cada detalhe do seu perfil..."):
            try:
                texto_cv = extrair_texto_pdf(pdf)
                
                # IA Analisa
                resposta = chamar_ia(SYSTEM_PROMPT, f"CURRÍCULO:\n{texto_cv}\n\nVAGA ALVO:\n{vaga}")
                
                st.session_state.resultado = resposta
                st.session_state.texto_cv = texto_cv
                st.session_state.vaga = vaga
                st.session_state.email = email
                
                nota = extrair_nota(resposta)
                salvar_no_sheets(email, nota, vaga, texto_cv, resposta, "")
                
            except Exception as e:
                st.error(f"Erro técnico: {e}")

# ---------------- RESULTADOS ----------------
if st.session_state.resultado:
    st.markdown("---")
    st.subheader("📊 Seu Diagnóstico")
    
    nota = extrair_nota(st.session_state.resultado)
    
    # Visual da Nota
    col_nota, col_texto = st.columns([1, 3])
    with col_nota:
        st.metric(label="Compatibilidade Atual", value=f"{nota}%")
    with col_texto:
        if nota > 75:
            st.success("Muito bom! Você tem grandes chances, mas podemos refinar.")
        elif nota > 50:
            st.warning("Tem potencial, mas o robô pode te barrar. Vamos ajustar?")
        else:
            st.error("Atenção: Seu currículo atual pode não passar. Precisamos de uma reforma.")

    st.write(st.session_state.resultado)
    
    st.markdown("---")
    st.info("💡 **Dica:** A IA pode reescrever seu currículo agora mesmo usando as palavras exatas que o robô quer ler.")
    
    if st.button("✨ Gerar Currículo Otimizado (Grátis)"):
        with st.spinner("Reescrevendo seu currículo para passar na vaga..."):
            try:
                novo_cv = chamar_ia(
                    OPTIMIZATION_PROMPT, 
                    f"CV ORIGINAL:\n{st.session_state.texto_cv}\n\nDIAGNÓSTICO:\n{st.session_state.resultado}"
                )
                
                st.subheader("📝 Sua Nova Versão")
                st.caption("Copie o texto abaixo e cole no Word/Docs para salvar seu novo PDF.")
                st.code(novo_cv, language="markdown")
                
                salvar_no_sheets(
                    st.session_state.email, 
                    100, 
                    st.session_state.vaga, 
                    st.session_state.texto_cv, 
                    st.session_state.resultado, 
                    novo_cv
                )
                
                st.balloons()
                st.success("Prontinho! Sucesso na aplicação! 🍀")
            except Exception as e:
                st.error(f"Erro ao gerar: {e}")
