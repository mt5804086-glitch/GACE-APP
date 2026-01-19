import streamlit as st
import pandas as pd
import os
from datetime import datetime
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURACIÓN (Estética OpositaTest) ---
st.set_page_config(page_title="GACE Academy Pro", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .question-card { 
        background-color: #ffffff; padding: 30px; border-radius: 15px; 
        border-left: 10px solid #1e40af; box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
        margin-bottom: 25px; 
    }
    .profile-banner { 
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); 
        color: white; padding: 20px; border-radius: 12px; margin-bottom: 30px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN A LA IA (Solución al error 404) ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Probamos con el nombre técnico completo que acepta la API v1beta
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error de conexión inicial: {e}")

# --- 3. GESTIÓN DE SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'quiz_step' not in st.session_state: st.session_state.quiz_step = 'menu'

# --- 4. FUNCIONES DE VALOR JURÍDICO ---
def consultar_ia(pregunta, correcta):
    # Prompt diseñado para tu perfil de Relaciones Laborales y MBA
    prompt = f"""
    Actúa como preparador experto para el Cuerpo de Gestión Administrativa (GACE). 
    El alumno tiene formación en RRHH y MBA. 
    Pregunta: {pregunta}
    Respuesta correcta: {correcta}
    
    INSTRUCCIÓN: Explica la base jurídica de la respuesta. 
    ES OBLIGATORIO CITAR EL ARTÍCULO Y LA LEY (ej. TREBEP, Ley 39/2015, Ley 40/2015).
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # Si falla el 1.5-flash, intentamos con el pro como plan B
        try:
            model_b = genai.GenerativeModel('models/gemini-pro')
            return model_b.generate_content(prompt).text
        except:
            return f"Error de acceso a la normativa. Por favor, verifica tu cuota en Google AI Studio. Detalles: {e}"

def registrar_progreso(tema, pregunta, seleccion, correcta, resultado):
    nueva_fila = pd.DataFrame([{
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "perfil": "RRHH_MBA",
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
    st.markdown('<div class="profile-banner">🎓 <b>Experto:</b> RRHH & MBA | <b>PL2 Euskera</b> | 📊 <b>Trazabilidad GSheets Activa</b></div>', unsafe_allow_html=True)
    st.title("📚 Módulos de Entrenamiento GACE")
    
    archivos = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.csv'))]
    if archivos:
        tema_sel = st.selectbox("Selecciona tu material de estudio:", archivos)
        n_preg = st.select_slider("Número de preguntas:", options=[5, 10, 15, 20], value=10)
        
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
            st.success(f"🎯 **¡CORRECTO!** La respuesta es la {correcta.upper()}")
            log_progreso(st.session_state.tema_n, row['Pregunta'], st.session_state.user_choice, correcta, "Acierto")
        else:
            st.error(f"❌ **FALLO.** Tu marcaste {st.session_state.user_choice.upper()} | Correcta: {correcta.upper()}")
            log_progreso(st.session_state.tema_n, row['Pregunta'], st.session_state.user_choice, correcta, "Fallo")

        st.divider()
        if st.button("✨ CONSULTAR BASE JURÍDICA (GEMINI AI)", type="primary"):
            with st.spinner("Conectando con la normativa vigente..."):
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
