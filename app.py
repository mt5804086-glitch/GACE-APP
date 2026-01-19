import streamlit as st
import pandas as pd
import os
from datetime import datetime
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# --- 1. ESTÉTICA PROFESIONAL (UX/UI) ---
st.set_page_config(page_title="GACE Academy Pro", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    .question-card { 
        background-color: #ffffff; 
        padding: 30px; 
        border-radius: 15px; 
        border-left: 10px solid #2563eb; 
        box-shadow: 0 4px 20px rgba(0,0,0,0.08); 
        margin-bottom: 25px; 
    }
    .stButton>button { border-radius: 10px; font-weight: bold; height: 3.8em; transition: 0.3s; }
    .stButton>button:hover { border: 2px solid #2563eb; transform: translateY(-2px); }
    .profile-banner { 
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); 
        color: white; padding: 20px; border-radius: 12px; margin-bottom: 30px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIONES Y SEGURIDAD ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Modelo actualizado para evitar el error 404
    model = genai.GenerativeModel('gemini-1.5-flash')
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de infraestructura: {e}")

# --- 3. GESTIÓN DE ESTADO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'quiz_step' not in st.session_state: st.session_state.quiz_step = 'menu'

# --- 4. FUNCIONES DE VALOR (IA y Registro) ---
def explicar_con_gemini(pregunta, correcta):
    prompt = f"Eres preparador GACE. Explica la base jurídica de: {pregunta}. Correcta: {correcta}. CITA ARTÍCULO Y LEY (TREBEP/Ley 39)."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"La IA está descansando: {e}"

def guardar_progreso(tema, pregunta, seleccion, correcta, resultado):
    """Registro de interoperabilidad (Art. 156 Ley 40/2015)."""
    nueva_fila = pd.DataFrame([{
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "tema": tema,
        "pregunta": pregunta[:100],
        "mi_respuesta": seleccion,
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

# --- 6. DASHBOARD (MBA STYLE) ---
if st.session_state.quiz_step == 'menu':
    st.markdown('<div class="profile-banner">🎓 <b>Experto:</b> RRHH & MBA | 🏆 <b>Objetivo:</b> GACE | 🌍 <b>PL2 (B2)</b></div>', unsafe_allow_html=True)
    st.title("📊 Selección de Módulo")
    
    archivos = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.csv'))]
    if archivos:
        tema_sel = st.selectbox("Elige tu material de estudio:", archivos)
        n_preg = st.select_slider("Número de preguntas:", options=[5, 10, 15, 20], value=10)
        
        if st.button("🚀 COMENZAR ENTRENAMIENTO"):
            df = pd.read_excel(tema_sel, engine='openpyxl') if tema_sel.endswith('.xlsx') else pd.read_csv(tema_sel)
            st.session_state.current_df = df.sample(n=min(n_preg, len(df))).reset_index(drop=True)
            st.session_state.current_idx = 0
            st.session_state.quiz_step = 'playing'
            st.session_state.feedback = False
            st.session_state.tema_nombre = tema_sel
            st.rerun()

# --- 7. MODO ENTRENAMIENTO (FUNCIONALIDAD COMPLETA) ---
elif st.session_state.quiz_step == 'playing':
    df = st.session_state.current_df
    idx = st.session_state.current_idx
    row = df.iloc[idx]
    
    # Barra de progreso real (OpositaTest)
    st.progress((idx + 1) / len(df))
    st.write(f"Pregunta {idx+1} de {len(df)}")
    
    st.markdown(f'<div class="question-card"><h3>{row["Pregunta"]}</h3></div>', unsafe_allow_html=True)
    
    opc = [row['Respuesta 1'], row['Respuesta 2'], row['Respuesta 3'], row['Respuesta 4']]
    let = ['a', 'b', 'c', 'd']

    if not st.session_state.feedback:
        for i, texto in enumerate(opc):
            if pd.notna(texto):
                # Botones de respuesta con sintaxis corregida
                if st.button(f"{let[i]}) {texto}", key=f"btn_{i}", use_container_width=True):
                    st.session_state.user_choice = let[i]
                    st.session_state.feedback = True
                    st.rerun()
    else:
        correcta = str(row['Respuesta']).strip().lower()
        es_acierto = (st.session_state.user_choice == correcta)
        
        if es_acierto:
            st.success(f"🎯 **¡ACIERTO!** La opción correcta es la {correcta.upper()}")
            res = "Acierto"
        else:
            st.error(f"❌ **FALLO.** Marcaste {st.session_state.user_choice.upper()} | Correcta: {correcta.upper()}")
            res = "Fallo"

        # Guardado en Google Sheets con detalle MBA
        guardar_progreso(st.session_state.tema_nombre, row['Pregunta'], st.session_state.user_choice, correcta, res)

        st.divider()
        if st.button("✨ CONSULTAR BASE JURÍDICA (GEMINI AI)", type="primary"):
            with st.spinner("Conectando con la normativa..."):
                st.info(explicar_con_gemini(row['Pregunta'], correcta))

        if st.button("Siguiente Pregunta ➡️"):
            if idx + 1 < len(df):
                st.session_state.current_idx += 1
                st.session_state.feedback = False
                st.rerun()
            else:
                st.session_state.quiz_step = 'menu'
                st.balloons()
                st.rerun()
