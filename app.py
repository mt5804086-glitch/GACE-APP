import streamlit as st
import pandas as pd
import os
from datetime import datetime
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURACIÓN PROFESIONAL ---
st.set_page_config(page_title="GACE Academy Pro", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .question-card { 
        background-color: #ffffff; padding: 25px; border-radius: 15px; 
        border-left: 10px solid #1e40af; box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
        margin-bottom: 20px; 
    }
    .profile-banner { 
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); 
        color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y DIAGNÓSTICO ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # Intentamos con el modelo más compatible (gemini-pro) para asegurar que funcione
    # Si este falla, el error nos dará una lista clara de qué modelos usar
    model = genai.GenerativeModel('gemini-pro') 
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de infraestructura: {e}")

# --- 3. ESTADO DE LA APP ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'quiz_step' not in st.session_state: st.session_state.quiz_step = 'menu'

# --- 4. FUNCIONES (MBA & RRHH) ---
def consultar_ia(pregunta, correcta):
    prompt = f"Como preparador GACE para un Graduado en RRHH, explica la base jurídica de: {pregunta}. Correcta: {correcta}. ES OBLIGATORIO CITAR ARTÍCULO Y LEY."
    try:
        # Intentamos generar contenido con el modelo estándar
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error al obtener base jurídica: {e}. Por favor, verifica tu API Key en Google AI Studio."

def log_gsheets(tema, pregunta, resultado):
    nueva_fila = pd.DataFrame([{
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "perfil": "MBA_RRHH",
        "tema": tema,
        "pregunta": pregunta[:80],
        "resultado": resultado
    }])
    try:
        df_actual = conn.read()
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(data=df_final)
    except: pass

# --- 5. INTERFAZ: LOGIN ---
if not st.session_state.logged_in:
    st.title("🔐 Acceso OpoTrainer Pro")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Acceder"):
        if u == "admin" and p == "1234":
            st.session_state.logged_in = True
            st.rerun()
    st.stop()

# --- 6. INTERFAZ: DASHBOARD ---
if st.session_state.quiz_step == 'menu':
    st.markdown('<div class="profile-banner">👨‍🎓 <b>Opositor:</b> RRHH & MBA | <b>PL2 Euskera</b> | 📊 <b>Trazabilidad Activa</b></div>', unsafe_allow_html=True)
    st.title("📚 Módulos de Entrenamiento")
    
    archivos = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.csv'))]
    if archivos:
        tema_sel = st.selectbox("Selecciona tu material:", archivos)
        n_preg = st.select_slider("Preguntas:", options=[5, 10, 15, 20], value=10)
        
        if st.button("🚀 INICIAR ENTRENAMIENTO"):
            df = pd.read_excel(tema_sel, engine='openpyxl') if tema_sel.endswith('.xlsx') else pd.read_csv(tema_sel)
            st.session_state.current_df = df.sample(n=min(n_preg, len(df))).reset_index(drop=True)
            st.session_state.current_idx = 0
            st.session_state.quiz_step = 'playing'
            st.session_state.feedback = False
            st.session_state.tema_n = tema_sel
            st.rerun()

# --- 7. MODO EXAMEN ---
elif st.session_state.quiz_step == 'playing':
    df = st.session_state.current_df
    idx = st.session_state.current_idx
    row = df.iloc[idx]
    
    st.progress((idx + 1) / len(df))
    st.markdown(f'<div class="question-card"><h3>{row["Pregunta"]}</h3></div>', unsafe_allow_html=True)
    
    opc = [row['Respuesta 1'], row['Respuesta 2'], row['Respuesta 3'], row['Respuesta 4']]
    let = ['a', 'b', 'c', 'd']

    if not st.session_state.feedback:
        for i, texto in enumerate(opc):
            if pd.notna(texto):
                if st.button(f"{let[i]}) {texto}", key=f"btn_{i}", use_container_width=True):
                    st.session_state.user_choice = let[i]
                    st.session_state.feedback = True
                    st.rerun()
    else:
        correcta = str(row['Respuesta']).strip().lower()
        acierto = (st.session_state.user_choice == correcta)
        
        if acierto:
            st.success(f"🎯 **¡CORRECTO!** Respuesta: {correcta.upper()}")
            log_gsheets(st.session_state.tema_n, row['Pregunta'], "Acierto")
        else:
            st.error(f"❌ **FALLO.** Marcaste {st.session_state.user_choice.upper()} | Correcta: {correcta.upper()}")
            log_gsheets(st.session_state.tema_n, row['Pregunta'], "Fallo")

        st.divider()
        if st.button("✨ VER BASE JURÍDICA (IA)", type="primary"):
            with st.spinner("Analizando normativa..."):
                st.info(consultar_ia(row['Pregunta'], correcta))

        if st.button("Siguiente Pregunta ➡️"):
            if idx + 1 < len(df):
                st.session_state.current_idx += 1
                st.session_state.feedback = False
                st.rerun()
            else:
                st.session_state.quiz_step = 'menu'
                st.balloons()
                st.rerun()
