import streamlit as st
import requests
import PyPDF2
import wikipedia
from PIL import Image
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
import tempfile
import re
import io
import os

# ==================== CONFIG ====================
st.set_page_config(page_title="Leo.AI PRO", page_icon="🦁", layout="wide")
st.markdown("<h1 style='text-align:center;color:#4B0082;'>🤖 Leo.AI – Tutor per la Maturità</h1>", unsafe_allow_html=True)

API_KEY = os.getenv("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")
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ==================== SESSION STATE ====================
if "renamed_chats" not in st.session_state:
    st.session_state.renamed_chats = {}

if "current_chat" not in st.session_state:
    st.session_state.current_chat = None

# ==================== COLORI PER MATERIA ====================
palette = {
    "Italiano": "#F7C6C7",
    "Storia": "#AEDFF7",
    "Matematica": "#C7F7C1",
    "Chimica": "#FFF3AE"
}

# ==================== Sidebar ====================
st.sidebar.header("📌 Tipo di risposta")
tipo_risposta = st.sidebar.radio("Seleziona tipo:", ["Normale con Wikipedia", "Riassunto"])

st.sidebar.markdown("---")

st.sidebar.header("📚 Materie")
selected_materia = st.sidebar.selectbox("Scegli materia:", list(palette.keys()))

st.sidebar.markdown("---")

st.sidebar.header("📝 Chat rinominate")
for nm in st.session_state.renamed_chats:
    if st.sidebar.button(nm):
        st.session_state.current_chat = nm

st.sidebar.markdown("---")

# ==================== FUNZIONI ====================
def read_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for p in reader.pages:
        if p.extract_text():
            text += p.extract_text() + "\n"
    return text

def wiki_search(q):
    try:
        s = wikipedia.search(q)
        if s:
            page = wikipedia.page(s[0])
            return page.content[:5000]
        return "Nessuna voce Wikipedia trovata."
    except Exception as e:
        return f"Errore Wikipedia: {e}"

def create_pdf(chat_messages, name):
    fn = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
    doc = SimpleDocTemplate(fn, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    for m in chat_messages:
        elements.append(Paragraph(f"{m['role']}: {m['content']}".replace("\n", "<br/>"), styles["Normal"]))
    doc.build(elements)
    return fn

def ask_groq(prompt, system_prompt):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role":"system","content":system_prompt},
            {"role":"user","content":prompt}
        ],
        "temperature":0.3,
        "max_completion_tokens":2000
    }
    try:
        r = requests.post(API_URL, headers=headers, json=data, timeout=120)
        res = r.json()
        if "choices" in res:
            return res["choices"][0]["message"]["content"]
        return "⚠️ Errore risposta"
    except Exception as e:
        return f"⚠️ Errore connessione: {e}"

def render_bubble(text, role):
    color = "#D3D3D3" if role=="user" else "#E8EAF6"
    return f"<div style='background:{color};padding:12px;border-radius:12px;margin:5px 0;'>{text}</div>"

# ==================== INPUT ====================
col1, col2 = st.columns([0.08, 0.92])
with col1:
    uploaded_file = st.file_uploader("📎 Premi per allegare", type=["pdf","png","jpg","jpeg"], label_visibility="collapsed")
with col2:
    user_input = st.chat_input("Scrivi la tua domanda...")

# Processa input
if user_input:
    # Contesto file
    context = ""
    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            context += "\nTESTO dal PDF:\n" + read_pdf(uploaded_file)
        else:
            context += "\nTESTO da immagine allegata.\n"

    # Wikipedia solo se richiesto
    if tipo_risposta == "Normale con Wikipedia":
        context += "\nWikipedia:\n" + wiki_search(user_input)

    sys_prompt = f"""
Sei Leo.AI, docente esperto in {selected_materia}.
Rispondi SOLO alla materia selezionata: {selected_materia}.
Non rispondere ad altre materie.
Rispondi in modo approfondito e chiaro.
"""
    if tipo_risposta == "Riassunto":
        sys_prompt += "Fornisci un riassunto sintetico.\n"

    prompt = sys_prompt + context + "\nDomanda:\n" + user_input

    with st.spinner("Leo sta generando la risposta..."):
        answer = ask_groq(prompt, sys_prompt)

    # Nome chat corretto
    chat_name = f"{selected_materia} - {user_input[:20].strip()}"

    # Se esiste già, aggiungi, altrimenti crea
    if chat_name not in st.session_state.renamed_chats:
        st.session_state.renamed_chats[chat_name] = []

    st.session_state.renamed_chats[chat_name].append({"role":"user","content":user_input})
    st.session_state.renamed_chats[chat_name].append({"role":"assistant","content":answer})
    st.session_state.current_chat = chat_name

# ==================== MOSTRA CHAT ====================
st.markdown("<hr>", unsafe_allow_html=True)

if st.session_state.current_chat:
    msgs = st.session_state.renamed_chats[st.session_state.current_chat]
    # Box con colore per materia
    bg = palette.get(selected_materia, "#FFFFFF")
    st.markdown(f"<div style='background:{bg};padding:15px;border-radius:15px;'>", unsafe_allow_html=True)

    for m in msgs:
        st.markdown(render_bubble(m["content"], m["role"]), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ==================== DOWNLOAD PDF ====================
if st.button("📥 Scarica chat come PDF"):
    if st.session_state.current_chat:
        pdf_file = create_pdf(st.session_state.renamed_chats[st.session_state.current_chat], st.session_state.current_chat)
        with open(pdf_file,"rb") as f:
            st.download_button("Scarica PDF", f, file_name=f"{st.session_state.current_chat}.pdf", mime="application/pdf")
