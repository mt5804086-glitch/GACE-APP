import streamlit as st
import pandas as pd
import os
import random
import time
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- ESTÉTICA ZENITH (DARK OLED PARA ANDROID Y IPHONE) ---
st.set_page_config(page_title="GACE OMNI", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #f8fafc; }
    .q-card {
        background: #0f172a; padding: 30px; border-radius: 20px;
        border: 1px solid #1e293b; border-top: 5px solid #6366f1;
        text-align: center; font-size: 1.4rem; font-weight: 600;
    }
    .stButton>button { border-radius: 12px; font-weight: 700; height: 4em; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN AL CEREBRO (GOOGLE SHEETS) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def fetch(ws): return conn.read(worksheet=ws).fillna("")
def push(df, ws): conn.update(worksheet=ws, data=df)

def sync_omni(q, res, user, t_resp):
    logs = fetch("stats_runs")
    new_log = pd.DataFrame([{"fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), "perfil": user, "tema": q['tema'], "resultado": res, "segundos": t_resp}])
    push(pd.concat([logs, new_log], ignore_index=True), "stats_runs")
    
    # Lógica de Niveles 1-2-3 segregada por perfil
    f_df = fetch("preguntas_falladas")
    mask = (f_df['Pregunta'] == q['pregunta']) & (f_df['Perfil'] == user)
    if res == "Fallo":
        if not mask.any():
            push(pd.concat([f_df, pd.DataFrame([{"Pregunta": q['pregunta'], "Tema": q['tema'], "Nivel": 1, "Perfil": user}])], ignore_index=True), "preguntas_falladas")
        else:
            f_df.loc[mask, 'Nivel'] = f_df.loc[mask, 'Nivel'].apply(lambda x: min(int(x) + 1, 3))
            push(f_df, "preguntas_falladas")
    elif res == "Acierto" and mask.any():
        if f_df.loc[mask, 'Nivel'].iloc[0] <= 1: f_df = f_df[~mask]
        else: f_df.loc[mask, 'Nivel'] -= 1
        push(f_df, "preguntas_falladas")

# --- NAVEGACIÓN ---
if 'step' not in st.session_state: st.session_state.step = 'home'
if 'historial' not in st.session_state: st.session_state.historial = {}

with st.sidebar:
    st.title("GACE OMNI")
    perfil = st.selectbox("👤 Perfil:", ["Julen", "Daniela"])
    st.divider()
    app_mode = st.radio("Sección:", ["📝 Entrenamiento", "📊 Duelo de Quesos"])
    if st.button("Finalizar Sesión"): st.session_state.step = 'results'

# (Aquí sigue el resto de la lógica de entrenamiento que hemos pulido)
# =========================================
# MODO ENTRENAMIENTO
# =========================================
if app_mode == "📝 Entrenamiento":
    if st.session_state.step == 'home':
        st.title(f"Plan de Vuelo: {perfil}")
        archivos = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.csv'))]
        n_preg = st.number_input("Preguntas:", 5, 200, 20)
        temas = st.multiselect("Temas:", archivos)
        
        if st.button("🚀 INICIAR"):
            pool = []
            for t in temas:
                df = pd.read_excel(t) if t.endswith('.xlsx') else pd.read_csv(t)
                for _, r in df.iterrows():
                    pool.append({"pregunta": r["Pregunta"], "tema": r["Tema"], "correcta": str(r["Respuesta"]).strip().lower(),
                                 "opciones": [r["Opción A"], r["Opción B"], r["Opción C"], r["Opción D"]]})
            if pool:
                random.shuffle(pool)
                st.session_state.data = pool[:n_preg]
                st.session_state.idx = 0
                st.session_state.historial = {}
                st.session_state.step = 'playing'
                st.rerun()

    elif st.session_state.step == 'playing':
        data = st.session_state.data
        idx = st.session_state.idx
        q = data[idx]
        
        st.markdown(f'<div class="q-card">{q["pregunta"]}</div>', unsafe_allow_html=True)
        
        letras = ['a', 'b', 'c', 'd']
        for i, opt in enumerate(q['opciones']):
            if pd.notna(opt):
                if st.button(f"{letras[i].upper()}) {opt}", key=f"{i}_{idx}"):
                    is_ok = (letras[i] == q['correcta'])
                    st.session_state.historial[idx] = {'ok': is_ok}
                    sync_omni(q, "Acierto" if is_ok else "Fallo", perfil, 0)
                    if idx + 1 < len(data):
                        st.session_state.idx += 1
                        st.rerun()
                    else:
                        st.session_state.step = 'results'
                        st.rerun()
# (Lógica simplificada para que quepa y sea operativa ya)
