import streamlit as st
import PyPDF2
from openai import OpenAI
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="IA de Carreira - Luana", layout="wide")

st.title("📄 Analisador & Otimizador de Currículos")
st.markdown("""
Esta ferramenta atua como sua parceira de carreira. 
Ela analisa a compatibilidade com a vaga e, se você quiser, reescreve o CV para passar nos robôs (ATS).
""")

# --- BARRA LATERAL (CONFIGURAÇÕES) ---
with st.sidebar:
    st.header("Configurações")
    api_key = st.text_input("Insira sua API Key da OpenAI", type="password")
    st.info("Para obter uma chave, vá em: platform.openai.com")

# --- FUNÇÕES UTILITÁRIAS ---
def extrair_texto_pdf(arquivo):
    """Lê o arquivo PDF e transforma em texto puro"""
    pdf_reader = PyPDF2.PdfReader(arquivo)
    texto = ""
    for page in pdf_reader.pages:
        texto += page.extract_text()
    return texto

def chamar_ia(prompt_sistema, prompt_usuario, chave):
    """Envia os dados para o GPT"""
    client = OpenAI(api_key=chave)
    response = client.chat.completions.create(
        model="gpt-4o", # Ou gpt-3.5-turbo
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

# --- SEU PROMPT MESTRE (O SEGREDO) ---
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

# --- INTERFACE PRINCIPAL ---

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Seu Currículo (PDF)")
    uploaded_file = st.file_uploader("Faça upload do PDF", type="pdf")

with col2:
    st.subheader("2. Descrição da Vaga")
    vaga_text = st.text_area("Cole a descrição completa aqui", height=200)

# Inicializa o estado da sessão (memória temporária do site)
if "analise_feita" not in st.session_state:
    st.session_state.analise_feita = False
if "texto_cv" not in st.session_state:
    st.session_state.texto_cv = ""

# --- BOTÃO DE ANÁLISE ---
if st.button("🔍 Analisar Aderência"):
    if not api_key:
        st.error("Por favor, insira a API Key na barra lateral.")
    elif not uploaded_file or not vaga_text:
        st.warning("Por favor, anexe o currículo e a descrição da vaga.")
    else:
        with st.spinner("Lendo currículo e comparando com a vaga..."):
            # 1. Extrair texto
            texto_cv = extrair_texto_pdf(uploaded_file)
            st.session_state.texto_cv = texto_cv # Guarda na memória
            
            # 2. Montar o pedido para a IA
            user_message = f"CURRÍCULO:\n{texto_cv}\n\nVAGA:\n{vaga_text}"
            
            # 3. Chamar a IA
            resultado = chamar_ia(SYSTEM_PROMPT, user_message, api_key)
            
            # 4. Mostrar resultado
            st.session_state.analise_resultado = resultado
            st.session_state.analise_feita = True
            st.session_state.vaga_original = vaga_text # Guarda para a fase 2

# --- EXIBIÇÃO DO RESULTADO FASE 1 ---
if st.session_state.analise_feita:
    st.markdown("---")
    st.subheader("💬 Feedback do Parceiro")
    st.write(st.session_state.analise_resultado)
    
    # --- BOTÃO DE OTIMIZAÇÃO (FASE 2) ---
    st.markdown("---")
    st.info("Gostou da análise? Quer gerar o documento final?")
    
    if st.button("✨ Sim, gerar Currículo Otimizado ATS"):
        with st.spinner("Reescrevendo seu currículo com as palavras-chave..."):
            
            # Monta o contexto para a IA lembrar do que leu
            contexto_fase_2 = f"""
            Contexto Anterior:
            O currículo original era: {st.session_state.texto_cv}
            A vaga era: {st.session_state.vaga_original}
            Sua análise foi: {st.session_state.analise_resultado}
            
            Ação:
            {OPTIMIZATION_INSTRUCTION}
            """
            
            # Chama a IA novamente
            resultado_final = chamar_ia(SYSTEM_PROMPT, contexto_fase_2, api_key)
            
            st.success("Currículo Gerado!")
            st.text_area("Copie seu novo CV abaixo:", value=resultado_final, height=600)
            
            # --- ÁREA DE APRENDIZADO (SALVAR DADOS) ---
            # Aqui simulamos o salvamento para você "aprender"
            import csv
            from datetime import datetime
            
            # Salva num arquivo CSV local chamado "banco_de_curriculos.csv"
            dados = [datetime.now(), st.session_state.vaga_original[:50], "Processado"]
            with open('banco_de_curriculos.csv', 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(dados)
            st.toast("Dados salvos no seu banco de aprendizado!")