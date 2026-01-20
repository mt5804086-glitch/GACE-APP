import streamlit as st
import pandas as pd
import os
import random
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(page_title="GACE OMNI", layout="wide")

# =========================================================
# ESTÉTICA
# =========================================================
st.markdown("""
<style>
.stApp { background-color: #000000; color: #f8fafc; }
.q-card {
    background: #0f172a;
    padding: 30px;
    border-radius: 20px;
    border: 1px solid #1e293b;
    border-top: 5px solid #6366f1;
    text-align: center;
    font-size: 1.4rem;
    font-weight: 600;
}
.stButton>button {
    border-radius: 12px;
    font-weight: 700;
    height: 4em;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# CONEXIÓN GSHEETS
# =========================================================
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def fetch(ws):
    return conn.read(worksheet=ws).fillna("")

def push(df, ws):
    conn.update(worksheet=ws, data=df)

# =========================================================
# ESTADO
# =========================================================
if "step" not in st.session_state:
    st.session_state.step = "home"
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "data" not in st.session_state:
    st.session_state.data = []
if "historial" not in st.session_state:
    st.session_state.historial = {}

# =========================================================
# SINCRONIZACIÓN OMNI
# =========================================================
def sync_omni(q, resultado, perfil, segundos=0):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    logs = fetch("stats_runs")
    logs = pd.concat([logs, pd.DataFrame([{
        "fecha": now,
        "perfil": perfil,
        "tema": q["tema"],
        "resultado": resultado,
        "segundos": segundos
    }])], ignore_index=True)
    push(logs, "stats_runs")

    fallos = fetch("preguntas_falladas")
    mask = (fallos["Pregunta"] == q["pregunta"]) & (fallos["Perfil"] == perfil)

    if resultado == "Fallo":
        if not mask.any():
            fallos = pd.concat([fallos, pd.DataFrame([{
                "Pregunta": q["pregunta"],
                "Tema": q["tema"],
                "Nivel": 1,
                "Perfil": perfil
            }])], ignore_index=True)
        else:
            fallos.loc[mask, "Nivel"] = fallos.loc[mask, "Nivel"].astype(int).clip(upper=3) + 1
    else:
        if mask.any():
            if fallos.loc[mask, "Nivel"].iloc[0] <= 1:
                fallos = fallos[~mask]
            else:
                fallos.loc[mask, "Nivel"] -= 1

    push(fallos.reset_index(drop=True), "preguntas_falladas")

# =========================================================
# CARGA DE PREGUNTAS
# =========================================================
def load_questions(files, n):
    pool = []

    for f in files:
        df = pd.read_excel(f) if f.endswith(".xlsx") else pd.read_csv(f)

        required = {
            "Pregunta", "Tema", "Respuesta",
            "Opción A", "Opción B", "Opción C", "Opción D"
        }
        if not required.issubset(df.columns):
            st.warning(f"⚠️ {f} ignorado (columnas incorrectas)")
            continue

        for _, r in df.iterrows():
            pool.append({
                "pregunta": r["Pregunta"],
                "tema": r["Tema"],
                "correcta": str(r["Respuesta"]).strip().lower(),
                "opciones": [
                    r["Opción A"], r["Opción B"],
                    r["Opción C"], r["Opción D"]
                ]
            })

    random.shuffle(pool)
    return pool[:n]

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.title("GACE OMNI")
    perfil = st.selectbox("👤 Perfil", ["Julen", "Daniela"])
    st.divider()
    app_mode = st.radio("Modo", ["📝 Entrenamiento"])
    if st.button("Finalizar sesión"):
        st.session_state.step = "results"

# =========================================================
# MODO ENTRENAMIENTO
# =========================================================
if app_mode == "📝 Entrenamiento":

    if st.session_state.step == "home":
        st.title(f"✈️ Plan de Vuelo · {perfil}")

        files = [f for f in os.listdir() if f.endswith((".xlsx", ".csv"))]
        n = st.number_input("Número de preguntas", 5, 200, 20)
        selected = st.multiselect("Selecciona temas", files)

        if st.button("🚀 INICIAR") and selected:
            st.session_state.data = load_questions(selected, n)
            st.session_state.idx = 0
            st.session_state.step = "playing"
            st.rerun()

    elif st.session_state.step == "playing":
        q = st.session_state.data[st.session_state.idx]

        st.progress((st.session_state.idx + 1) / len(st.session_state.data))
        st.markdown(f'<div class="q-card">{q["pregunta"]}</div>', unsafe_allow_html=True)

        letras = ["a", "b", "c", "d"]
        for i, opt in enumerate(q["opciones"]):
            if pd.notna(opt):
                if st.button(f"{letras[i].upper()}) {opt}", key=f"q{st.session_state.idx}_{i}"):
                    ok = letras[i] == q["correcta"]
                    sync_omni(q, "Acierto" if ok else "Fallo", perfil)

                    if st.session_state.idx + 1 < len(st.session_state.data):
                        st.session_state.idx += 1
                    else:
                        st.session_state.step = "results"
                    st.rerun()

    elif st.session_state.step == "results":
        st.title("🏁 Sesión finalizada")
        st.success("Entrenamiento completado")
        if st.button("Volver al inicio"):
            st.session_state.step = "home"
            st.rerun()
