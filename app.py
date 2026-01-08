import streamlit as st
import PyPDF2
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="IA de Carreira - Luana", layout="wide")

st.title("📄 Analisador & Otimizador de Currículos")

# --- CONEXÃO COM GOOGLE SHEETS ---
def salvar_no_sheets(vaga, nota, status):
    """Salva os dados na planilha do Google"""
    try:
        # Define o escopo de acesso (Drive e Sheets)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Pega as credenciais do Cofre do Streamlit
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )
        
        # Conecta
        gc = gspread.authorize(credentials)
        
        # Abre a planilha (TEM QUE SER O NOME EXATO QUE VOCÊ CRIOU)
        sh = gc.open("Banco de Curriculos") 
        worksheet = sh.sheet1
        
        # Adiciona a linha
        dados = [str(datetime.now()), vaga[:50], status, nota]
        worksheet.append_row(dados)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Sheets: {e}")
        return False

# --- FUNÇÕES UTILITÁRIAS ---
def extrair_texto_pdf(arquivo):
    pdf_reader = PyPDF2.PdfReader(arquivo)
    texto = ""
    for page in pdf_reader.pages:
        texto += page.extract_text()
    return texto

def chamar_ia(prompt_sistema, prompt_usuario):
    # Pega a chave do Cofre automaticamente
    api_key = st.secrets[""] 
    client = OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model="gpt-4o", 
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

# --- SEU PROMPT MESTRE ---
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
- Integre palavras-chave da vaga.
- Resumo Profissional focado na senioridade da vaga.
- Experiência com verbos fortes (Liderou, Criou, Estruturou) e resultados no topo.
- Formatação limpa (Markdown), pronta para copiar.
"""

# --- INTERFACE ---
col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("Seu Currículo (PDF)", type="pdf")
with col2:
    vaga_text = st.text_area("Descrição da Vaga", height=200)

if "analise_feita" not in st.session_state:
    st.session_state.analise_feita = False

# BOTÃO 1: ANALISAR
if st.button("🔍 Analisar"):
    if uploaded_file and vaga_text:
        with st.spinner("Analisando..."):
            texto_cv = extrair_texto_pdf(uploaded_file)
            st.session_state.texto_cv = texto_cv
            st.session_state.vaga_original = vaga_text
            
            # Monta o prompt
            msg = f"CV: {texto_cv}\n\nVaga: {vaga_text}"
            resultado = chamar_ia(SYSTEM_PROMPT, msg)
            
            st.session_state.analise_resultado = resultado
            st.session_state.analise_feita = True
            
            # Salva no Sheets
            salvar_no_sheets(vaga_text, "N/A", "Analisado - Fase 1")
            st.toast("Análise salva no banco de dados!")

# EXIBIÇÃO E BOTÃO 2
if st.session_state.analise_feita:
    st.write(st.session_state.analise_resultado)
    
    if st.button("✨ Gerar Currículo Otimizado"):
        with st.spinner("Escrevendo..."):
            ctx = f"""
            Contexto Anterior:
            O currículo original era: {st.session_state.texto_cv}
            A vaga era: {st.session_state.vaga_original}
            Sua análise foi: {st.session_state.analise_resultado}
            
            Ação:
            {OPTIMIZATION_INSTRUCTION}
            """
            final = chamar_ia(SYSTEM_PROMPT, ctx)
            st.write(final)
            
            # Salva a segunda etapa no Sheets
            salvar_no_sheets(st.session_state.vaga_original, "100", "Gerado CV Novo")
            st.success("Salvo e Gerado!")
