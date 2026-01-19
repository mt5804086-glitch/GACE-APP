import streamlit as st
import pandas as pd
import os
from datetime import datetime
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="OpoTrainer AI - GACE", page_icon="⚖️", layout="wide")

# --- VERIFICACIÓN DE SECRETOS ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("⚠️ Error: No se encuentra la GEMINI_API_KEY en los Secrets de Streamlit.")
    st.stop()

# --- CONEXIONES (Gemini y Google Sheets) ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Usamos el modelo flash que es rápido y estable
    model = genai.GenerativeModel('gemini-1.5-flash')
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Error al conectar con los servicios: {e}")

# --- GESTIÓN DE SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'quiz_step' not in st.session_state: st.session_state.quiz_step = 'menu'

# --- FUNCIONES CORE ---
def explicar_con_gemini(pregunta, opciones, correcta, respuesta_usuario):
    """Función para obtener la base jurídica según el perfil del usuario."""
    prompt = f"""
    Eres un preparador experto de oposiciones para un alumno Graduado en Relaciones Laborales y MBA.
    Analiza la siguiente pregunta de examen:
    Pregunta: {pregunta}
    Opciones: {opciones}
    Respuesta correcta: {correcta}
    Respuesta del alumno: {respuesta_usuario}

    INSTRUCCIÓN OBLIGATORIA: Explica de forma profesional por qué la respuesta correcta es esa. 
    Debes citar específicamente el NÚMERO DE ARTÍCULO y la LEY a la que pertenece (ej. TREBEP, Ley 39/2015, Ley 40/2015, etc.).
    """
    response = model.generate_content(prompt)
    return response.text

def registrar_progreso(tema, pregunta, mi_resp, correcta, resultado):
    """Guarda el resultado en Google Sheets para trazabilidad MBA."""
    nueva_fila = pd.DataFrame([{
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "tema": tema,
        "pregunta": pregunta[:100],
        "resultado": resultado
    }])
    try:
        df_actual = conn.read()
        df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
        conn.update(data=df_final)
        return True
    except:
        return False

# --- INTERFAZ: LOGIN ---
if not st.session_state.logged_in:
    st.title("🔐 Acceso OpoTrainer Pro")
    col1, col2 = st.columns(2)
    with col1:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            if u == "admin" and p == "1234":
                st.session_state.logged_in = True
                st.rerun()
    st.stop()

# --- INTERFAZ: DASHBOARD ---
if st.session_state.quiz_step == 'menu':
    st.title("📊 Panel de Control de Estudio")
    st.info(f"Perfil: Relaciones Laborales & MBA | Euskera: PL2 (B2)")
    
    archivos = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.csv'))]
    if not archivos:
        st.warning("No se han encontrado archivos de preguntas (.xlsx o .csv) en el repositorio.")
    else:
        tema_sel = st.selectbox("Selecciona el tema a trabajar:", archivos)
        if st.button("🚀 Iniciar Entrenamiento"):
            # Cargamos con engine openpyxl para evitar errores de formato
            df = pd.read_excel(tema_sel, engine='openpyxl') if tema_sel.endswith('.xlsx') else pd.read_csv(tema_sel)
            st.session_state.current_df = df.sample(n=min(10, len(df))).reset_index(drop=True)
            st.session_state.current_idx = 0
            st.session_state.quiz_step = 'playing'
            st.session_state.feedback = False
            st.session_state.tema_nombre = tema_sel
            st.rerun()

# --- INTERFAZ: MODO TEST ---
elif st.session_state.quiz_step == 'playing':
    df = st.session_state.current_df
    idx = st.session_state.current_idx
    row = df.iloc[idx]
    
    st.write(f"**Pregunta {idx+1} de {len(df)}**")
    st.markdown(f"### {row['Pregunta']}")
    
    opciones = [row['Respuesta 1'], row['Respuesta 2'], row['Respuesta 3'], row['Respuesta 4']]
    letras = ['a', 'b', 'c', 'd']

    if not st.session_state.feedback:
        for i, texto_opt in enumerate(opciones):
            if pd.notna(texto_opt):
                if st.button(f"{letras[i]}) {texto_opt}", key=f"opt_{i}", use_container_width=True):
                    st.session_state.user_choice = letras[i]
                    st.session_state.feedback = True
                    st.rerun()
    else:
        # Procesar Respuesta
        correcta = str(row['Respuesta']).strip().lower()
        acierto = (st.session_state.user_choice == correcta)
        
        if acierto:
            st.success(f"✅ ¡CORRECTO! La respuesta es la {correcta.upper()}")
            resultado_txt = "Acierto"
        else:
            st.error(f"❌ FALLO. Tu respuesta: {st.session_state.user_choice.upper()} | Correcta: {correcta.upper()}")
            resultado_txt = "Fallo"

        # Guardar en Google Sheets (Interoperabilidad Art. 156 Ley 40/2015)
        registrar_progreso(st.session_state.tema_nombre, row['Pregunta'], st.session_state.user_choice, correcta, resultado_txt)

        # Botón Gemini
        st.divider()
        if st.button("✨ CONSULTAR BASE JURÍDICA (IA GEMINI)", type="primary"):
            with st.spinner("Analizando legislación vigente..."):
                explicacion = explicar_con_gemini(row['Pregunta'], opciones, correcta, st.session_state.user_choice)
                st.info(explicacion)

        if st.button("Siguiente Pregunta ➡️"):
            if idx + 1 < len(df):
                st.session_state.current_idx += 1
                st.session_state.feedback = False
                st.rerun()
            else:
                st.session_state.quiz_step = 'menu'
                st.success("¡Has terminado el bloque de test!")
                st.rerun()
