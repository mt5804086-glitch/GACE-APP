import streamlit as st
import pandas as pd
import os
from datetime import datetime
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN TÉCNICA (MBA & Eficacia Art. 3 Ley 40/2015) ---
st.set_page_config(page_title="GACE Academy Pro", page_icon="📈", layout="wide")

# Diseño visual estilo OpositaTest
st.markdown("""
    <style>
    .stApp { background-color: #f1f5f9; }
    .question-card { background-color: #ffffff; padding: 2rem; border-radius: 12px; border-left: 10px solid #1d4ed8; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); margin-bottom: 25px; }
    .stButton>button { border-radius: 8px; font-weight: bold; transition: 0.2s; height: 3em; }
    .stProgress > div > div > div > div { background-color: #1d4ed8; }
    .profile-banner { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 15px; border-radius: 10px; margin-bottom: 25px; }
    </style>
    """, unsafe_allow_html=True)

# --- INFRAESTRUCTURA ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Probamos el modelo flash, si da 404 el sistema lo gestionará en la función de consulta
    model = genai.GenerativeModel('gemini-1.5-flash')
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de infraestructura: {e}")

# --- GESTIÓN DE SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'quiz_step' not in st.session_state: st.session_state.quiz_step = 'menu'

# --- LÓGICA DE INTELIGENCIA JURÍDICA ---
def consultar_base_legal(pregunta, correcta):
    """Consulta a Gemini con fallback para evitar error 404."""
    prompt = f"""
    Eres preparador de oposiciones GACE para un Graduado en RRHH y MBA. 
    Pregunta: {pregunta}
    Respuesta correcta: {correcta}
    INSTRUCCIÓN: Explica brevemente la base jurídica. ES OBLIGATORIO CITAR EL ARTÍCULO Y LA LEY (TREBEP, Ley 39/2015, etc.).
    """
    try:
        # Intento con el modelo principal
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        # Fallback manual: si falla el 1.5-flash, intentamos con el pro estándar
        try:
            model_alt = genai.GenerativeModel('gemini-pro')
            response = model_alt.generate_content(prompt)
            return response.text
        except Exception as e2:
            return f"Error al conectar con la base legal: {e2}. Verifica tu cuota en Google AI Studio."

def log_gsheets(tema, pregunta, resultado):
    """Registro de interoperabilidad (Art. 156 Ley 40/2015)."""
    nueva_fila = pd.DataFrame([{
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "perfil": "RRHH_MBA_PL2",
        "tema": tema,
        "pregunta": pregunta[:100],
        "resultado": resultado
    }])
    try:
        df_actual = conn.read()
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(data=df_final)
    except: pass

# --- INTERFAZ ---
if not st.session_state.logged_in:
    st.title("🛡️ Acceso Seguro OpoTrainer")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Acceder"):
        if u == "admin" and p == "1234":
            st.session_state.logged_in = True
            st.rerun()
    st.stop()

# --- DASHBOARD (ESTILO MBA) ---
if st.session_state.quiz_step == 'menu':
    st.markdown('<div class="profile-banner">🎓 <b>Perfil:</b> Relaciones Laborales & MBA | 🏆 <b>Idioma:</b> PL2 (B2 Euskera)</div>', unsafe_allow_html=True)
    st.title("📊 Control de Módulos GACE")
    
    archivos = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.csv'))]
    if archivos:
        tema = st.selectbox("Selecciona el material de estudio:", archivos)
        cant = st.select_slider("Número de preguntas para esta sesión:", options=[5, 10, 15, 20], value=10)
        
        if st.button("🚀 INICIAR ENTRENAMIENTO"):
            df = pd.read_excel(tema, engine='openpyxl') if tema.endswith('.xlsx') else pd.read_csv(tema)
            st.session_state.current_df = df.sample(n=min(cant, len(df))).reset_index(drop=True)
            st.session_state.current_idx = 0
            st.session_state.quiz_step = 'playing'
            st.session_state.feedback = False
            st.session_state.tema_n = tema
            st.rerun()

# --- MODO TEST (FUNCIONALIDAD OPOSITATEST) ---
elif st.session_state.quiz_step == 'playing':
    df = st.session_state.current_df
    idx = st.session_state.current_idx
    row = df.iloc[idx]
    
    # Barra de progreso real
    st.progress((idx + 1) / len(df))
    st.write(f"Pregunta {idx+1} de {len(df)}")

    # Visualización de pregunta profesional
    st.markdown(f'<div class="question-card"><h3>{row["Pregunta"]}</h3></div>', unsafe_allow_html=True)
    
    opciones = [row['Respuesta 1'], row['Respuesta 2'], row['Respuesta 3'], row['Respuesta 4']]
    letras = ['a', 'b', 'c', 'd']

    if not st.session_state.feedback:
        for i, opt in enumerate(opciones):
            if pd.notna(opt):
                if st.button(f
