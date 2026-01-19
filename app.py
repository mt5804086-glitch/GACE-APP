import streamlit as st
import pandas as pd
import os
from datetime import datetime
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE ALTO NIVEL (Perfil MBA & RRHH) ---
st.set_page_config(page_title="OpoTrainer GACE - Sistema Inteligente", page_icon="⚖️", layout="wide")

# Diseño visual avanzado (CSS personalizado)
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .question-card { background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 8px solid #1e40af; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .stButton>button { border-radius: 10px; height: 3.5em; font-weight: bold; transition: 0.3s; }
    .stButton>button:hover { background-color: #1e40af; color: white; transform: translateY(-2px); }
    .status-bar { padding: 10px; border-radius: 8px; background-color: #e2e8f0; margin-bottom: 20px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- INFRAESTRUCTURA (Secrets y Conexiones) ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # SELECCIÓN DE MODELO ESTABLE (Para evitar el error 404)
    model = genai.GenerativeModel('gemini-1.5-flash')
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error en el despliegue de infraestructura: {e}")

# --- GESTIÓN DE SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'quiz_step' not in st.session_state: st.session_state.quiz_step = 'menu'

# --- LÓGICA DE NEGOCIO ---
def obtener_base_juridica(pregunta, opciones, correcta):
    """Genera la explicación legal obligatoria citando Artículo y Ley."""
    prompt = f"""
    Eres preparador de oposiciones para un Graduado en RRHH y MBA.
    Pregunta: {pregunta}
    Opciones: {opciones}
    Respuesta correcta: {correcta}
    
    INSTRUCCIÓN: Explica la base jurídica. ES OBLIGATORIO citar el ARTÍCULO y la LEY (ej. TREBEP, Ley 39/2015, etc.).
    """
    response = model.generate_content(prompt)
    return response.text

def registrar_progreso(tema, pregunta, resultado):
    """Interoperabilidad con Google Sheets (Art. 156 Ley 40/2015)."""
    nueva_fila = pd.DataFrame([{
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "perfil": "RRHH_MBA_PL2",
        "tema": tema,
        "pregunta": pregunta[:80],
        "resultado": resultado
    }])
    try:
        df_actual = conn.read()
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(data=df_final)
        return True
    except: return False

# --- PANTALLA: ACCESO SEGURO ---
if not st.session_state.logged_in:
    st.title("🔐 Acceso OpoTrainer Pro")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Acceder"):
        if u == "admin" and p == "1234":
            st.session_state.logged_in = True
            st.rerun()
    st.stop()

# --- PANTALLA: DASHBOARD (MÉTODO OPOSITATEST) ---
if st.session_state.quiz_step == 'menu':
    st.markdown(f'<div class="status-bar">👤 Experto: Relaciones Laborales & MBA | Idioma: Euskera PL2</div>', unsafe_allow_html=True)
    st.title("📚 Módulos de Entrenamiento GACE")
    
    archivos = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.csv'))]
    col1, col2 = st.columns([2, 1])
    with col1:
        tema = st.selectbox("Elige el tema a estudiar:", archivos)
    with col2:
        cantidad = st.slider("Nº de preguntas:", 5, 20, 10)

    if st.button("🚀 INICIAR TEST"):
        df = pd.read_excel(tema, engine='openpyxl') if tema.endswith('.xlsx') else pd.read_csv(tema)
        st.session_state.current_df = df.sample(n=min(cantidad, len(df))).reset_index(drop=True)
        st.session_state.current_idx = 0
        st.session_state.quiz_step = 'playing'
        st.session_state.feedback = False
        st.session_state.nombre_tema = tema
        st.rerun()

# --- PANTALLA: SIMULACIÓN DE EXAMEN ---
elif st.session_state.quiz_step == 'playing':
    df = st.session_state.current_df
    idx = st.session_state.current_idx
    row = df.iloc[idx]
    
    st.progress((idx + 1) / len(df))
    st.markdown(f'<div class="question-card"><h3>{row["Pregunta"]}</h3></div>', unsafe_allow_html=True)
    
    opciones = [row['Respuesta 1'], row['Respuesta 2'], row['Respuesta 3'], row['Respuesta 4']]
    letras = ['a', 'b', 'c', 'd']

    if not st.session_state.feedback:
        for i, opt in enumerate(opciones):
            if pd.notna(opt):
                if st.button(f"{letras[i]}) {opt}", key=f"ans_{i}", use_container_width=True):
                    st.session_state.user_choice = letras[i]
                    st.session_state.feedback = True
                    st.rerun()
    else:
        # Corrección y Trazabilidad
        correcta = str(row['Respuesta']).strip().lower()
        acierto = (st.session_state.user_choice == correcta)
        
        if acierto:
            st.success(f"🎯 **ACIERTO.** La respuesta correcta es la {correcta.upper()}")
            res_val = "Acierto"
        else:
            st.error(f"❌ **FALLO.** Marcaste {st.session_state.user_choice.upper()} | Correcta: {correcta.upper()}")
            res_val = "Fallo"

        registrar_progreso(st.session_state.nombre_tema, row['Pregunta'], res_val)

        # Botón Gemini (Base Jurídica)
        st.divider()
        if st.button("✨ CONSULTAR BASE JURÍDICA (GEMINI AI)", type="primary"):
            with st.spinner("Analizando legislación..."):
                st.info(obtener_base_juridica(row['Pregunta'], opciones, correcta))

        if st.button("Siguiente Pregunta ➡️"):
            if idx + 1 < len(df):
                st.session_state.current_idx += 1
                st.session_state.feedback = False
                st.rerun()
            else:
                st.session_state.quiz_step = 'menu'
                st.balloons()
                st.rerun()
