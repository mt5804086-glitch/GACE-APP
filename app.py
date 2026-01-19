import streamlit as st
import pandas as pd
import os
from datetime import datetime
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="OpoTrainer AI Pro", page_icon="🎓", layout="wide")

# --- ESTILOS ---
st.markdown("""
    <style>
    .question-card { background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 5px solid #007bff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .feedback-box { padding: 15px; border-radius: 10px; margin-top: 10px; font-weight: bold; }
    .stButton>button { border-radius: 12px; height: 3.5em; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIONES ---
# Cargamos Gemini y Google Sheets desde los Secrets que ya pegaste
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de configuración: {e}")

# --- SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'quiz_step' not in st.session_state: st.session_state.quiz_step = 'menu'
if 'historial_sesion' not in st.session_state: st.session_state.historial_sesion = []

# --- FUNCIONES ---
def consultar_gemini(pregunta, opciones, correcta, mi_respuesta):
    prompt = f"""
    Eres preparador de oposiciones para un alumno Graduado en RRHH y MBA. 
    Pregunta: {pregunta}
    Opciones: {opciones}
    Respuesta correcta: {correcta}
    Respuesta alumno: {mi_respuesta}
    
    Explica de forma profesional por qué es esa la respuesta. 
    ES OBLIGATORIO citar ARTÍCULO y LEY (ej. TREBEP o Ley 39/2015).
    """
    response = model.generate_content(prompt)
    return response.text

def guardar_en_sheets(tema, pregunta, mi_resp, correcta, resultado):
    # 1. Crear el nuevo registro
    nueva_fila = pd.DataFrame([{
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "usuario": "admin",
        "tema": tema,
        "pregunta": pregunta[:100],
        "mi_respuesta": mi_resp,
        "respuesta_correcta": correcta,
        "resultado": resultado
    }])
    
    # 2. Leer datos actuales, juntar y subir (Aquí es donde se activa la magia)
    try:
        df_actual = conn.read()
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(data=df_final)
        return True
    except:
        return False

# --- LOGIN ---
if not st.session_state.logged_in:
    st.title("🔐 Acceso OpoTrainer")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if u == "admin" and p == "1234":
            st.session_state.logged_in = True
            st.rerun()
    st.stop()

# --- MENÚ PRINCIPAL ---
if st.session_state.quiz_step == 'menu':
    st.title("📊 Dashboard de Opositor")
    st.write(f"Perfil: RRHH & MBA | Idioma: B2 Euskera")
    
    # Cargar archivos
    files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.csv'))]
    tema = st.selectbox("Elige el tema a estudiar:", files)
    
    if st.button("🚀 EMPEZAR TEST"):
        df = pd.read_csv(tema) if tema.endswith('.csv') else pd.read_excel(tema)
        st.session_state.current_df = df.sample(n=min(10, len(df))).reset_index(drop=True)
        st.session_state.current_idx = 0
        st.session_state.quiz_step = 'playing'
        st.session_state.feedback_view = False
        st.session_state.tema_nombre = tema
        st.rerun()

# --- MODO JUEGO ---
elif st.session_state.quiz_step == 'playing':
    df = st.session_state.current_df
    idx = st.session_state.current_idx
    row = df.iloc[idx]
    
    st.progress((idx + 1) / len(df))
    st.markdown(f"<div class='question-card'><h3>{row['Pregunta']}</h3></div>", unsafe_allow_html=True)
    
    letras = ['a', 'b', 'c', 'd']
    opciones = [row['Respuesta 1'], row['Respuesta 2'], row['Respuesta 3'], row['Respuesta 4']]

    if not st.session_state.feedback_view:
        for i, opt in enumerate(opciones):
            if pd.notna(opt):
                if st.button(f"{letras[i]}) {opt}", key=f"ans_{i}", use_container_width=True):
                    st.session_state.user_choice = letras[i]
                    st.session_state.feedback_view = True
                    st.rerun()
    else:
        # RESULTADOS Y BOTÓN GEMINI (AQUÍ APARECERÁ)
        correcta = str(row['Respuesta']).strip().lower()
        acierto = (st.session_state.user_choice == correcta)
        
        if acierto:
            st.success(f"¡CORRECTO! Era la {correcta.upper()}")
            res_txt = "Acierto"
        else:
            st.error(f"FALLO. Marcaste {st.session_state.user_choice.upper()}, era la {correcta.upper()}")
            res_txt = "Fallo"

        # GUARDAR EN GOOGLE SHEETS AUTOMÁTICAMENTE
        if 'last_saved' not in st.session_state or st.session_state.last_saved != idx:
            exito = guardar_en_sheets(st.session_state.tema_nombre, row['Pregunta'], st.session_state.user_choice, correcta, res_txt)
            st.session_state.last_saved = idx
            if exito: st.toast("Datos guardados en Google Sheets ✅")

        # --- BOTÓN DE GEMINI ---
        st.divider()
        if st.button("✨ CONSULTAR BASE JURÍDICA (GEMINI AI)", type="primary"):
            with st.spinner("Analizando leyes..."):
                explicacion = consultar_gemini(row['Pregunta'], opciones, correcta, st.session_state.user_choice)
                st.info(explicacion)

        if st.button("Siguiente Pregunta ➡️"):
            if idx + 1 < len(df):
                st.session_state.current_idx += 1
                st.session_state.feedback_view = False
                st.rerun()
            else:
                st.session_state.quiz_step = 'menu'
                st.rerun()
