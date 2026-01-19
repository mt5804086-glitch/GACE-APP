import streamlit as st
import pandas as pd
import os
import time
import altair as alt
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="OpoTrainer PRO", page_icon="🎓", layout="wide")

# --- ESTILOS "OPOSITATEST" ---
st.markdown("""
    <style>
    .question-box { background-color: #f9f9f9; padding: 25px; border-radius: 15px; border-left: 5px solid #007bff; margin-bottom: 20px; }
    .correct { background-color: #d4edda; color: #155724; padding: 15px; border-radius: 10px; margin-top: 10px; }
    .incorrect { background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 10px; margin-top: 10px; }
    .stButton>button { border-radius: 20px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE SESIÓN ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'history' not in st.session_state: st.session_state.history = [] # Para el dashboard
if 'progreso_preguntas' not in st.session_state: st.session_state.progreso_preguntas = {}

# --- FUNCIONES AUXILIARES ---
def buscar_tests():
    return sorted([f for f in os.listdir('.') if f.endswith(('.xlsx', '.csv'))])

@st.cache_data
def cargar_datos(nombre):
    df = pd.read_csv(nombre) if nombre.endswith('.csv') else pd.read_excel(nombre)
    df.columns = df.columns.str.strip()
    if 'ID' not in df.columns: df['ID'] = df.index.astype(str) + "_" + nombre
    return df

# --- LOGIN (Simplificado para la prueba) ---
if not st.session_state.logged_in:
    st.title("🔐 Acceso OpoTrainer")
    with st.form("login"):
        user = st.text_input("Usuario")
        passw = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            if user == "admin" and passw == "1234":
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
    st.stop()

# ==========================================
# ☰ MENÚ LATERAL PRO
# ==========================================
with st.sidebar:
    st.title(f"🚀 OpoTrainer")
    st.write(f"Hola, {st.session_state.user}")
    menu = st.radio("Menú", ["🏠 Panel de Control", "📝 Nuevo Examen", "📊 Estadísticas PRO"])
    st.divider()
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.rerun()

# ==========================================
# 🏠 PANEL DE CONTROL (DASHBOARD)
# ==========================================
if menu == "🏠 Panel de Control":
    st.title("Tu Progreso Diario")
    
    # Métricas rápidas
    c1, c2, c3 = st.columns(3)
    total_hechas = len(st.session_state.history)
    c1.metric("Preguntas Hoy", total_hechas)
    c2.metric("Nivel de Acierto", f"{85 if total_hechas > 0 else 0}%")
    c3.metric("Días en racha", "1")

    # Gráfico de actividad (Simulado con los datos de la sesión)
    if st.session_state.history:
        st.subheader("Actividad de hoy")
        df_hist = pd.DataFrame(st.session_state.history)
        chart = alt.Chart(df_hist).mark_bar().encode(
            x='time:T', y='count()', color=alt.Color('result', scale=alt.Scale(range=['#dc3545', '#28a745']))
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Aún no has hecho tests hoy. ¡Empieza uno!")

# ==========================================
# 📝 NUEVO EXAMEN (LÓGICA PASO A PASO)
# ==========================================
elif menu == "📝 Nuevo Examen":
    if 'quiz_state' not in st.session_state:
        st.session_state.quiz_state = 'config'

    if st.session_state.quiz_state == 'config':
        st.header("Configura tu sesión")
        tests = buscar_tests()
        archivo = st.selectbox("Elige el tema:", tests)
        
        col1, col2 = st.columns(2)
        with col1:
            num_preg = st.number_input("Número de preguntas:", 5, 100, 10)
            modo = st.radio("Filtro:", ["Todo mezclado", "Solo las que fallo (Rojo)", "Solo nuevas/media"])
        with col2:
            feedback = st.toggle("Feedback instantáneo", value=True)
            shuffle = st.toggle("Barajar opciones", value=True)

        if st.button("🚀 EMPEZAR TEST", type="primary"):
            df = cargar_datos(archivo)
            # Aplicar filtros de dificultad aquí si se desea
            st.session_state.current_df = df.sample(n=min(num_preg, len(df))).reset_index(drop=True)
            st.session_state.quiz_state = 'playing'
            st.session_state.current_idx = 0
            st.session_state.respuestas_examen = {}
            st.session_state.feedback_mostrado = False
            st.rerun()

    elif st.session_state.quiz_state == 'playing':
        df = st.session_state.current_df
        idx = st.session_state.current_idx
        
        # Barra de progreso
        progreso = (idx + 1) / len(df)
        st.progress(progreso, text=f"Pregunta {idx + 1} de {len(df)}")

        # Tarjeta de pregunta
        row = df.iloc[idx]
        st.markdown(f"<div class='question-box'><h3>{row['Pregunta']}</h3></div>", unsafe_allow_html=True)

        # Opciones
        opciones = [row['Respuesta 1'], row['Respuesta 2'], row['Respuesta 3'], row['Respuesta 4']]
        letras = ['a', 'b', 'c', 'd']
        
        # Mostrar botones de respuesta
        for i, opt in enumerate(opciones):
            if pd.notna(opt):
                if st.button(f"{letras[i]}) {opt}", key=f"btn_{idx}_{i}", use_container_width=True):
                    st.session_state.respuestas_examen[idx] = letras[i]
                    st.session_state.feedback_mostrado = True

        # Feedback Instantáneo
        if st.session_state.feedback_mostrado:
            resp_usuario = st.session_state.respuestas_examen[idx]
            correcta = str(row['Respuesta']).strip().lower()
            
            if resp_usuario == correcta:
                st.markdown("<div class='correct'>✅ <b>¡Correcto!</b></div>", unsafe_allow_html=True)
                res_val = "Acierto"
            else:
                st.markdown(f"<div class='incorrect'>❌ <b>Incorrecto.</b> La respuesta era la <b>{correcta}</b>.</div>", unsafe_allow_html=True)
                res_val = "Fallo"

            # Guardar en histórico para el dashboard
            st.session_state.history.append({"time": datetime.now(), "result": res_val})
            
            if st.button("Siguiente Pregunta ➡️"):
                if idx + 1 < len(df):
                    st.session_state.current_idx += 1
                    st.session_state.feedback_mostrado = False
                    st.rerun()
                else:
                    st.session_state.quiz_state = 'results'
                    st.rerun()

    elif st.session_state.quiz_state == 'results':
        st.title("🏆 Examen Finalizado")
        # Aquí iría un resumen detallado
        if st.button("Volver al Inicio"):
            st.session_state.quiz_state = 'config'
            st.rerun()

# ==========================================
# 📊 ESTADÍSTICAS PRO
# ==========================================
elif menu == "📊 Estadísticas PRO":
    st.title("Dashboard de Rendimiento")
    st.write("Análisis detallado de tus puntos débiles.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("¿Dónde fallas más?")
        # Gráfico simulado por categorías
        data = pd.DataFrame({'Tema': ['Constitución', 'TREBEP', 'Procedimiento'], 'Fallos': [12, 5, 18]})
        st.altair_chart(alt.Chart(data).mark_bar().encode(y='Tema', x='Fallos', color='Tema'), use_container_width=True)
    with col2:
        st.subheader("Evolución de Nota")
        evol = pd.DataFrame({'Día': [1,2,3,4,5], 'Nota': [4.5, 5.2, 5.8, 6.5, 7.2]})
        st.altair_chart(alt.Chart(evol).mark_line(point=True).encode(x='Día', y='Nota'), use_container_width=True)
