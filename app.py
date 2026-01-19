import streamlit as st
import pandas as pd
import time
import altair as alt # Librería para gráficos bonitos

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="OpoTrainer Pro", page_icon="🧠", layout="centered")

# --- ESTILOS VISUALES (CSS) ---
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #ddd;
    }
    /* Colores para las etiquetas de dificultad */
    .dif-facil { color: #28a745; font-weight: bold; }
    .dif-media { color: #ffc107; font-weight: bold; }
    .dif-dificil { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIÓN DE ESTADO (MEMORIA) ---
# Aquí guardamos en qué "carpeta" está cada pregunta
if 'progreso_preguntas' not in st.session_state:
    st.session_state.progreso_preguntas = {} # Diccionario: {id_pregunta: 'Media'}

# Por defecto, todas las preguntas nacen en "Media" si no se han hecho nunca
def obtener_dificultad(pregunta_id):
    return st.session_state.progreso_preguntas.get(pregunta_id, "Media")

def actualizar_dificultad(pregunta_id, acierto):
    estado_actual = obtener_dificultad(pregunta_id)
    
    if acierto:
        # Si aciertas: Dificil -> Media -> Facil
        if estado_actual == "Difícil": nuevo = "Media"
        else: nuevo = "Fácil"
    else:
        # Si fallas: Directo a Difícil
        nuevo = "Difícil"
    
    st.session_state.progreso_preguntas[pregunta_id] = nuevo

# --- FUNCIONES DE CARGA ---
@st.cache_data
def cargar_datos(archivo):
    if archivo.name.endswith('.csv'):
        try: df = pd.read_csv(archivo)
        except: df = pd.read_csv(archivo, sep=';', encoding='latin-1')
    else:
        df = pd.read_excel(archivo)
    df.columns = df.columns.str.strip()
    return df

# ==========================================
# ☰ BARRA LATERAL (MENÚ)
# ==========================================
with st.sidebar:
    st.title("🧠 OpoTrainer")
    
    modo = st.radio(
        "Modo de Estudio:",
        ["🏠 Inicio", "📝 Hacer Test", "📈 Mis Resultados"]
    )
    
    st.divider()
    
    # VISUALIZACIÓN DE CARPETAS
    # Contamos cuántas preguntas hay en cada nivel
    total = len(st.session_state.progreso_preguntas)
    faciles = list(st.session_state.progreso_preguntas.values()).count("Fácil")
    medias = list(st.session_state.progreso_preguntas.values()).count("Media")
    dificiles = list(st.session_state.progreso_preguntas.values()).count("Difícil")
    
    st.markdown("### 🗂️ Tus Carpetas")
    st.progress(faciles / (total if total > 0 else 1), text=f"🟢 Fáciles: {faciles}")
    st.progress(medias / (total if total > 0 else 1), text=f"🟡 Medias: {medias}")
    st.progress(dificiles / (total if total > 0 else 1), text=f"🔴 Difíciles: {dificiles}")

# ==========================================
# 🏠 INICIO
# ==========================================
if modo == "🏠 Inicio":
    st.title("Sistema de Repetición")
    st.info("Este sistema mueve las preguntas de carpeta automáticamente según tus aciertos.")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Fáciles", faciles, "Dominadas")
    col2.metric("🟡 Medias", medias, "Por repasar")
    col3.metric("🔴 Difíciles", dificiles, "Prioridad")

# ==========================================
# 📝 HACER TEST
# ==========================================
elif modo == "📝 Hacer Test":
    if 'examen_activo' not in st.session_state:
        st.session_state.examen_activo = False

    # --- CONFIGURACIÓN ---
    if not st.session_state.examen_activo:
        st.header("Configura tu sesión")
        archivo = st.file_uploader("Sube el archivo de preguntas", type=['xlsx', 'csv'])
        
        if archivo:
            st.divider()
            
            # FILTRO POR DIFICULTAD (LO QUE PEDISTE)
            st.subheader("¿Qué quieres practicar hoy?")
            filtro_dificultad = st.multiselect(
                "Selecciona carpetas:",
                ["Fácil", "Media", "Difícil"],
                default=["Media", "Difícil"] # Por defecto no mostramos las fáciles
            )
            
            orden = st.radio("Orden:", ["Aleatorio", "Normal"], horizontal=True)
            
            if st.button("🚀 COMENZAR", type="primary"):
                df = cargar_datos(archivo)
                # Crear IDs únicos para las preguntas si no tienen
                if 'ID' not in df.columns:
                    df['ID'] = df.index.astype(str) # Usamos el índice como ID simple
                
                # Filtrar según dificultad
                # (Creamos una columna temporal 'Dificultad' en el dataframe para filtrar)
                df['Estado_Temp'] = df['ID'].apply(obtener_dificultad)
                df_filtrado = df[df['Estado_Temp'].isin(filtro_dificultad)]
                
                if len(df_filtrado) == 0:
                    st.error("No hay preguntas en esas carpetas todavía. Selecciona 'Media' para empezar.")
                else:
                    if orden == "Aleatorio":
                        df_filtrado = df_filtrado.sample(frac=1).reset_index(drop=True)
                    
                    st.session_state.df_activo = df_filtrado
                    st.session_state.examen_activo = True
                    st.session_state.respuestas_temp = {}
                    st.rerun()

    # --- PANTALLA DEL TEST ---
    else:
        df = st.session_state.df_activo
        
        # BARRA DE ESTADO SUPERIOR
        c1, c2 = st.columns([1, 5])
        if c1.button("🔙 Salir"):
            st.session_state.examen_activo = False
            st.rerun()
        c2.progress(len(st.session_state.respuestas_temp) / len(df), text=f"Progreso: {len(st.session_state.respuestas_temp)}/{len(df)}")

        # MOSTRAMOS LAS PREGUNTAS
        with st.form("test_form"):
            for i, row in df.iterrows():
                # INDICADOR VISUAL DE DIFICULTAD
                estado = obtener_dificultad(row['ID'])
                color_icono = "🟢" if estado == "Fácil" else "🔴" if estado == "Difícil" else "🟡"
                
                st.markdown(f"**{i+1}. {row['Pregunta']}** <small>({color_icono} {estado})</small>", unsafe_allow_html=True)
                
                # Opciones
                opciones = []
                for k in range(1, 5):
                    if f'Respuesta {k}' in row and pd.notna(row[f'Respuesta {k}']):
                        opciones.append(f"{chr(96+k)}) {row[f'Respuesta {k}']}")
                
                # Guardamos respuesta
                st.session_state.respuestas_temp[row['ID']] = st.radio(
                    "R:", opciones, key=f"q_{row['ID']}", label_visibility="collapsed", index=None
                )
                st.markdown("---")
            
            # BOTÓN FINAL
            if st.form_submit_button("🏁 CORREGIR Y ACTUALIZAR CARPETAS"):
                aciertos = 0
                fallos = 0
                
                st.header("📊 Resultados del Sesión")
                
                for i, row in df.iterrows():
                    user_res = st.session_state.respuestas_temp.get(row['ID'])
                    if user_res:
                        letra_user = user_res[0]
                        letra_correcta = str(row['Respuesta']).strip().lower()
                        
                        es_correcta = (letra_user == letra_correcta)
                        
                        # --- LA MAGIA: ACTUALIZAR DIFICULTAD ---
                        actualizar_dificultad(row['ID'], es_correcta)
                        
                        # MOSTRAR FEEDBACK VISUAL
                        if es_correcta:
                            aciertos += 1
                            st.success(f"✅ Pregunta {i+1}: Correcta. (Se mueve a carpeta más fácil)")
                        else:
                            fallos += 1
                            with st.expander(f"❌ Pregunta {i+1}: Fallo (Se mueve a DIFÍCIL)", expanded=True):
                                st.write(f"Tu respuesta: {letra_user} | Correcta: **{letra_correcta}**")
                                st.info(f"Solución: {row.get(f'Respuesta {ord(letra_correcta)-96}', '')}")
                
                # --- GRÁFICOS AL FINAL (LO QUE PEDISTE) ---
                st.divider()
                st.subheader("📈 Rendimiento Visual")
                
                col_g1, col_g2 = st.columns(2)
                
                # Gráfico 1: Tarta Aciertos/Fallos
                datos_grafico = pd.DataFrame({
                    'Categoría': ['Aciertos', 'Fallos'],
                    'Valor': [aciertos, fallos]
                })
                with col_g1:
                    grafico_tarta = alt.Chart(datos_grafico).mark_arc(innerRadius=50).encode(
                        theta=alt.Theta(field="Valor", type="quantitative"),
                        color=alt.Color(field="Categoría", type="nominal", scale=alt.Scale(domain=['Aciertos', 'Fallos'], range=['#28a745', '#dc3545']))
                    ).properties(title="Resumen de la Sesión")
                    st.altair_chart(grafico_tarta, use_container_width=True)

                # Gráfico 2: Barras de dificultad actual
                data_dif = pd.DataFrame({
                    'Nivel': ['Fácil', 'Media', 'Difícil'],
                    'Cantidad': [
                        list(st.session_state.progreso_preguntas.values()).count("Fácil"),
                        list(st.session_state.progreso_preguntas.values()).count("Media"),
                        list(st.session_state.progreso_preguntas.values()).count("Difícil")
                    ]
                })
                with col_g2:
                    grafico_barras = alt.Chart(data_dif).mark_bar().encode(
                        x='Nivel',
                        y='Cantidad',
                        color=alt.Color('Nivel', scale=alt.Scale(domain=['Fácil', 'Media', 'Difícil'], range=['#28a745', '#ffc107', '#dc3545']))
                    ).properties(title="Estado Actual de tu Base de Datos")
                    st.altair_chart(grafico_barras, use_container_width=True)

# ==========================================
# 📈 PANTALLA: RESULTADOS GLOBALES
# ==========================================
elif modo == "📈 Mis Resultados":
    st.title("Tu Evolución")
    st.write("Aquí verás gráficos históricos de cómo vas vaciando la carpeta 'Difícil'.")
    # (Aquí podríamos poner más gráficos complejos en el futuro)
