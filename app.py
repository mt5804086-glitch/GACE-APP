import streamlit as st
import pandas as pd
import os
from datetime import datetime
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURACIÓN PROFESIONAL (Estilo OpositaTest) ---
st.set_page_config(page_title="GACE Pro Training", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f0f2f6; }
    .question-card { 
        background-color: #ffffff; 
        padding: 30px; 
        border-radius: 15px; 
        border-left: 10px solid #1e40af; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
        margin-bottom: 25px; 
    }
    .stButton>button { 
        border-radius: 12px; 
        font-weight: bold; 
        height: 3.5em; 
        transition: 0.3s; 
    }
    .stButton>button:hover { border: 2px solid #1e40af; transform: translateY(-2px); }
    .profile-banner { 
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); 
        color: white; 
        padding: 20px; 
        border-radius: 12px; 
        margin-bottom: 30px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INFRAESTRUCTURA Y SECRETOS ---
try:
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("Falta GEMINI_API_KEY en los Secrets.")
        st.stop()
    
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión: {e}")

# --- 3. GESTIÓN DE SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'quiz_step' not in st.session_state: st.session_state.quiz_step = 'menu'

# --- 4. LÓGICA DE NEGOCIO (IA y Registro) ---
def consultar_gemini_legal(pregunta, correcta):
    """Fallback para evitar el error 404 y forzar citas legales."""
    prompt = f"Como preparador de GACE para un MBA/RRHH, explica la base jurídica de: {pregunta}. Correcta: {correcta}. ES OBLIGATORIO CITAR ARTÍCULO Y LEY."
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        # Intento con modelo alternativo si el flash falla (Error 404)
        try:
            alt_model = genai.GenerativeModel('gemini-pro')
            return alt_model.generate_content(prompt).text
        except Exception as e:
            return f"Error de conexión con la IA: {e}"

def registrar_progreso_gsheets(tema, pregunta, mi_resp, correcta, resultado):
    """Garantiza la interoperabilidad según Art. 156 Ley 40/2015."""
    nueva_fila = pd.DataFrame([{
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "perfil": "RRHH_MBA_PL2",
        "tema": tema,
        "pregunta": pregunta[:100],
        "mi_respuesta": mi_resp,
        "correcta": correcta,
        "resultado": resultado
    }])
    try:
        df_actual = conn.read()
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(data=df_final)
    except: pass

# --- 5. INTERFAZ: LOGIN ---
if not st.session_state.logged_in:
    st.title("🛡️ Acceso Seguro OpoTrainer")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Acceder"):
        if u == "admin" and p == "1234":
            st.session_state.logged_in = True
            st.rerun()
    st.stop()

# --- 6. INTERFAZ: DASHBOARD ---
if st.session_state.quiz_step == 'menu':
    st.markdown('<div class="profile-banner">🎓 <b>Experto:</b> RRHH & MBA | 🏆 <b>Objetivo:</b> GACE Euskadi | 🌍 <b>PL2</b></div>', unsafe_allow_html=True)
    st.title("📊 Panel de Gestión de Estudio")
    
    archivos = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.csv'))]
    if archivos:
        tema_sel = st.selectbox("Selecciona tu módulo:", archivos)
        num_q = st.select_slider("Preguntas:", options=[5, 10, 15, 20], value=10)
        
        if st.button("🚀 INICIAR ENTRENAMIENTO"):
            df = pd.read_excel(tema_sel, engine='openpyxl') if tema_sel.endswith('.xlsx') else pd.read_csv(tema_sel)
            st.session_state.current_df = df.sample(n=min(num_q, len(df))).reset_index(drop=True)
            st.session_state.current_idx = 0
            st.session_state.quiz_step = 'playing'
            st.session_state.feedback = False
            st.session_state.tema_nombre = tema_sel
            st.rerun()

# --- 7. INTERFAZ: MODO TEST ---
elif st.session_state.quiz_step == 'playing':
    df = st.session_state.current_df
    idx = st.session_state.current_idx
    row = df.iloc[idx]
    
    st.progress((idx + 1) / len(df))
    st.write(f"Pregunta {idx+1} de {len(df)}")
    st.markdown(f'<div class="question-card"><h3>{row["Pregunta"]}</h3></div>', unsafe_allow_html=True)
    
    opciones = [row['Respuesta 1'], row['Respuesta 2'], row['Respuesta 3'], row['Respuesta 4']]
    letras = ['a', 'b', 'c', 'd']

    if not st.session_state.feedback:
        for i, texto in enumerate(opciones):
            if pd.notna(texto):
                # FIX: Sintaxis cerrada correctamente aquí
                if st.button(f"{letras[i]}) {texto}", key=f"btn_{i}", use_container_width=True):
                    st.session_state.user_choice = letras[i]
                    st.session_state.feedback = True
                    st.rerun()
    else:
        correcta = str(row['Respuesta']).strip().lower()
        acierto = (st.session_state.user_choice == correcta)
        
        if acierto:
            st.success(f"🎯 **¡CORRECTO!** La respuesta es la {correcta.upper()}")
            resultado = "Acierto"
        else:
            st.error(f"❌ **FALLO.** Marcaste {st.session_state.user_choice.upper()} | Correcta: {correcta.upper()}")
            resultado = "Fallo"

        registrar_progreso_gsheets(st.session_state.tema_nombre, row['Pregunta'], st.session_state.user_choice, correcta, resultado)

        st.divider()
        if st.button("✨ CONSULTAR BASE JURÍDICA (GEMINI AI)", type="primary"):
            with st.spinner("Analizando normativa..."):
                st.info(consultar_gemini_legal(row['Pregunta'], correcta))

        if st.button("Siguiente Pregunta ➡️"):
            if idx + 1 < len(df):
                st.session_state.current_idx += 1
                st.session_state.feedback = False
                st.rerun()
            else:
                st.session_state.quiz_step = 'menu'
                st.balloons()
                st.rerun()
