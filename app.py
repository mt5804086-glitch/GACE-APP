import streamlit as st
import pandas as pd
import os
import time
import altair as alt

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="OpoTrainer Base de Datos", page_icon="🗄️", layout="centered")

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-weight: bold; }
    .dif-facil { color: #28a745; font-weight: bold; }
    .dif-media { color: #ffc107; font-weight: bold; }
    .dif-dificil { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN PARA ENCONTRAR TUS 200 ARCHIVOS ---
def buscar_tests():
    # Busca todos los archivos en la carpeta actual
    archivos = os.listdir('.')
    # Se queda solo con los Excel o CSV
    lista = [f for f in archivos if f.endswith(('.xlsx', '.csv'))]
    return sorted(lista)

# --- MEMORIA DE DIFICULTAD ---
if 'progreso_preguntas' not in st.session_state:
    st.session_state.progreso_preguntas = {}

def obtener_dificultad(pid):
    return st.session_state.progreso_preguntas.get(pid, "Media")

def actualizar_dificultad(pid, acierto):
    actual = obtener_dificultad(pid)
    if acierto:
        nuevo = "Media" if actual == "Difícil" else "Fácil"
    else:
        nuevo = "Difícil"
    st.session_state.progreso_preguntas[pid] = nuevo

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos(nombre_archivo):
    try:
        if nombre_archivo.endswith('.csv'):
            try: df = pd.read_csv(nombre_archivo)
            except: df = pd.read_csv(nombre_archivo, sep=';', encoding='latin-1')
        else:
            df = pd.read_excel(nombre_archivo)
        df.columns = df.columns.str.strip()
        # Crear ID si no existe
        if 'ID' not in df.columns:
            df['ID'] = df.index.astype(str) + "_" + nombre_archivo
        return df
    except:
        return None

# ==========================================
# ☰ MENÚ LATERAL
# ==========================================
with st.sidebar:
    st.title("🗄️ Tu Biblioteca")
    
    # BUSCAR ARCHIVOS AUTOMÁTICAMENTE
    mis_tests = buscar_tests()
    
    if not mis_tests:
        st.error("⚠️ No encuentro archivos Excel/CSV en GitHub.")
    else:
        st.success(f"✅ {len(mis_tests)} Tests disponibles")

    modo = st.radio("Navegación:", ["🏠 Inicio", "📝 Hacer Test", "📈 Resultados"])
    
    if st.button("🔄 Refrescar Lista"):
        st.rerun()

# ==========================================
# 🏠 INICIO
# ==========================================
if modo == "🏠 Inicio":
    st.title("OpoTrainer: Base de Datos")
    if not mis_tests:
        st.warning("⚠️ Parece que no has subido los Excels a GitHub todavía.")
        st.write("Sube tus archivos .xlsx o .csv a la misma carpeta donde está app.py")
    else:
        st.write(f"Tienes **{len(mis_tests)} documentos** listos para practicar.")
        st.info("Ve a la pestaña 'Hacer Test' y elige uno del desplegable.")

# ==========================================
# 📝 HACER TEST (CON LISTA DESPLEGABLE)
# ==========================================
elif modo == "📝 Hacer Test":
    if 'examen_activo' not in st.session_state:
        st.session_state.examen_activo = False

    # --- SELECCIÓN DE TEST ---
    if not st.session_state.examen_activo:
        st.header("1️⃣ Elige el Tema")
        
        if mis_tests:
            # AQUÍ ESTÁ LA CLAVE: LISTA DESPLEGABLE
            archivo_elegido = st.selectbox("Selecciona un documento:", mis_tests)
            
            st.divider()
            st.header("2️⃣ Configuración")
            c1, c2 = st.columns(2)
            with c1:
                filtro = st.multiselect("Dificultad:", ["Fácil", "Media", "Difícil"], default=["Media", "Difícil"])
            with c2:
                orden = st.radio("Orden:", ["Normal", "Aleatorio"])
            
            if st.button("🚀 CARGAR ESTE TEST", type="primary"):
                df = cargar_datos(archivo_elegido)
                if df is not None:
                    # Filtrar y ordenar...
                    df['Estado_Temp'] = df['ID'].apply(obtener_dificultad)
                    df = df[df['Estado_Temp'].isin(filtro)]
                    
                    if not df.empty:
                        if orden == "Aleatorio":
                            df = df.sample(frac=1).reset_index(drop=True)
                        st.session_state.df_activo = df
                        st.session_state.examen_activo = True
                        st.session_state.respuestas_temp = {}
                        st.rerun()
                    else:
                        st.warning("No hay preguntas de esa dificultad en este test.")
        else:
            st.error("Sube archivos a GitHub primero.")

    # --- PANTALLA DE PREGUNTAS (IGUAL QUE ANTES) ---
    else:
        df = st.session_state.df_activo
        col_salir, col_bar = st.columns([1, 4])
        if col_salir.button("🔙 Volver"):
            st.session_state.examen_activo = False
            st.rerun()
        
        col_bar.progress(len(st.session_state.respuestas_temp)/len(df))
        
        with st.form("test_activo"):
            for i, row in df.iterrows():
                estado = obtener_dificultad(row['ID'])
                icono = "🟢" if estado == "Fácil" else "🔴" if estado == "Difícil" else "🟡"
                st.markdown(f"**{i+1}. {row['Pregunta']}** <small>({icono})</small>", unsafe_allow_html=True)
                
                opciones = []
                for k in range(1, 5):
                    if f'Respuesta {k}' in row and pd.notna(row[f'Respuesta {k}']):
                        opciones.append(f"{chr(96+k)}) {row[f'Respuesta {k}']}")
                
                st.session_state.respuestas_temp[row['ID']] = st.radio("R:", opciones, key=f"q_{row['ID']}", index=None, label_visibility="collapsed")
                st.markdown("---")
            
            if st.form_submit_button("🏁 CORREGIR"):
                aciertos = 0
                for i, row in df.iterrows():
                    resp = st.session_state.respuestas_temp.get(row['ID'])
                    if resp:
                        correcta = str(row['Respuesta']).strip().lower()
                        es_ok = (resp[0] == correcta)
                        actualizar_dificultad(row['ID'], es_ok)
                        if es_ok: aciertos += 1
                        else: st.error(f"Fallo en pregunta {i+1}. Correcta: {correcta}")
                
                st.balloons()
                st.metric("Nota", f"{(aciertos/len(df))*10:.2f}")

# ==========================================
# 📈 RESULTADOS
# ==========================================
elif modo == "📈 Resultados":
    st.title("Estadísticas Globales")
    difs = list(st.session_state.progreso_preguntas.values())
    tot = len(difs)
    if tot > 0:
        st.bar_chart({
            "Verde (Fácil)": difs.count("Fácil"),
            "Amarillo (Media)": difs.count("Media"),
            "Rojo (Difícil)": difs.count("Difícil")
        })
    else:
        st.info("Haz algún test para generar datos.")
