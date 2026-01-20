import streamlit as st
import pandas as pd
import os
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIGURACIÓN Y CSS PROFESIONAL ---
st.set_page_config(page_title="GACE Pro Suite", layout="wide", page_icon="⚖️")

# Definimos la paleta de colores profesional
COLOR_PRIMARY = "#4f46e5"  # Índigo
COLOR_SUCCESS = "#10b981"  # Esmeralda
COLOR_DANGER = "#ef4444"   # Rojo
COLOR_BG_LIGHT = "#f8fafc" # Gris muy claro

st.markdown(f"""
    <style>
    /* Importamos fuente moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    
    .stApp {{ background-color: {COLOR_BG_LIGHT}; }}
    
    /* Headers */
    .main-header {{
        font-size: 2.2rem; font-weight: 800; color: #1e293b; margin-bottom: 0.5rem;
        letter-spacing: -0.025em;
    }}
    .sub-header {{
        font-size: 1.25rem; font-weight: 600; color: #334155; margin-top: 2.5rem; margin-bottom: 1rem;
        border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem;
    }}

    /* Tarjetas de Métricas (KPIs) */
    .metric-card {{
        background-color: white; padding: 25px; border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        text-align: left; border: 1px solid #e2e8f0; transition: transform 0.2s;
    }}
    .metric-card:hover {{ transform: translateY(-2px); }}
    .metric-icon {{ font-size: 1.5rem; margin-bottom: 10px; }}
    .metric-label {{ font-size: 0.875rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }}
    .metric-value {{ font-size: 2.5rem; font-weight: 800; color: #0f172a; line-height: 1.2; }}
    
    /* Entorno de Test */
    .quiz-header {{
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 20px; color: #475569; font-weight: 600;
    }}
    .question-box {{ 
        padding: 35px; border-radius: 20px; margin-bottom: 25px; background: white; 
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-top: 6px solid {COLOR_PRIMARY};
        font-size: 1.15rem; font-weight: 600; color: #1e293b;
    }}

    /* Botones de Respuesta Mejorados */
    .stButton>button {{ 
        width: 100%; border-radius: 12px; border: 2px solid #e2e8f0; background-color: white;
        color: #334155; font-weight: 600; padding: 15px; height: auto;
        transition: all 0.2s ease-in-out;
    }}
    .stButton>button:hover {{ 
        border-color: {COLOR_PRIMARY}; color: {COLOR_PRIMARY}; background-color: #eef2ff; 
        box-shadow: 0 4px 6px rgba(79, 70, 229, 0.1);
    }}

    /* Tarjetas de Resultado Animadas */
    @keyframes fadeInUp {{ from {{ opacity: 0; transform: translate3d(0, 20px, 0); }} to {{ opacity: 1; transform: none; }} }}
    .result-card {{
        padding: 25px; border-radius: 15px; margin-top: 20px; animation: fadeInUp 0.4s ease-out;
        color: white; font-weight: 600; display: flex; align-items: center;
    }}
    .result-success {{ background-color: {COLOR_SUCCESS}; box-shadow: 0 10px 15px -3px rgba(16, 185, 129, 0.3); }}
    .result-danger {{ background-color: {COLOR_DANGER}; box-shadow: 0 10px 15px -3px rgba(239, 68, 68, 0.3); }}
    .result-icon {{ font-size: 1.8rem; margin-right: 15px; }}
    .result-text span {{ display: block; font-size: 0.9rem; opacity: 0.9; font-weight: 400; margin-top: 4px; }}

    /* Personalización de Barra de Progreso */
    .stProgress > div > div > div > div {{ background-color: {COLOR_PRIMARY}; }}

    /* Ocultar elementos de Streamlit */
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}}
    [data-testid="stSidebarNav"] {{ border-right: 1px solid #e2e8f0; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y CACHÉ DE DATOS ---
@st.cache_resource
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

conn = get_conn()

@st.cache_data(ttl=60)
def load_analysis_data():
    try:
        df = conn.read()
        df['fecha'] = pd.to_datetime(df['fecha'], format="%d/%m/%Y %H:%M", errors='coerce')
        # Limpieza de nombres de temas largos para los gráficos
        df['tema_corto'] = df['tema'].astype(str).str.replace('.xlsx', '').str.replace('.csv', '').str.slice(0, 15)
        return df
    except Exception as e:
        return pd.DataFrame()

# --- 3. LÓGICA DE SESIÓN Y REGISTRO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'quiz_step' not in st.session_state: st.session_state.quiz_step = 'config'
if 'feedback_shown' not in st.session_state: st.session_state.feedback_shown = False

def registrar_dato(tema, pregunta_texto, resultado):
    pregunta_corta = pregunta_texto[:150] + "..." if len(pregunta_texto) > 150 else pregunta_texto
    fila = pd.DataFrame([{
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), 
        "tema": tema, 
        "pregunta": pregunta_corta, 
        "resultado": resultado
    }])
    try:
        df = conn.read()
        if 'pregunta' not in df.columns: df['pregunta'] = "Pregunta antigua"
        conn.update(data=pd.concat([df, fila], ignore_index=True))
        load_analysis_data.clear() 
    except Exception: pass

# --- 4. LOGIN MINIMALISTA ---
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div style="text-align: center; margin-top: 50px;"><h1 style="color: #4f46e5;">⚖️ GACE Pro Suite</h1><p>Acceso Seguro</p></div>', unsafe_allow_html=True)
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Iniciar Sesión", type="primary", use_container_width=True):
            if u == "admin" and p == "1234":
                st.session_state.logged_in = True
                st.rerun()
    st.stop()

# =========================================
# NAVEGACIÓN LATERAL (SIDEBAR)
# =========================================
with st.sidebar:
    st.markdown('<div style="margin-bottom: 20px;"><h2 style="color: #4f46e5;">Menú Principal</h2></div>', unsafe_allow_html=True)
    # Usamos iconos en las opciones para mejor aspecto visual
    app_mode = st.radio("", ["📝 Zona de Entrenamiento", "📊 Dashboard Analítico"], label_visibility="collapsed")
    st.divider()
    st.markdown(f"""
        <div style='background: #e0e7ff; padding: 15px; border-radius: 12px; color: #3730a3;'>
            <div style='font-weight: 600;'>👤 Perfil Activo</div>
            <div style='font-size: 0.9rem;'>MBA & RRHH | PL2</div>
        </div>
    """, unsafe_allow_html=True)

# =========================================
# MODO 1: ZONA DE ENTRENAMIENTO
# =========================================
if "Entrenamiento" in app_mode:
    
    if st.session_state.quiz_step == 'config':
        st.markdown('<div class="main-header">Configuración de Sesión</div><p>Prepara tu entorno de estudio.</p>', unsafe_allow_html=True)
        st.divider()
        
        archivos = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.csv'))]
        
        if archivos:
            col_tema, col_opts = st.columns([2, 1])
            with col_tema:
                tema_sel = st.selectbox("📂 Selecciona el Módulo Normativo:", archivos)
            
            with col_opts:
                cantidad = st.number_input("🔢 Nº de Preguntas:", min_value=5, max_value=50, value=10, step=5)

            st.write("") # Espacio
            
            col_modo, col_inicio = st.columns(2)
            with col_modo:
                modo = st.radio("🔀 Modo de Selección:", ["Aleatorio (Repaso)", "Secuencial (Estudio)"], horizontal=True)
            
            offset = 0
            with col_inicio:
                if "Secuencial" in modo:
                     offset = st.number_input("⏭️ Empezar desde pregunta nº:", min_value=1, value=1) - 1
                else:
                     st.write("") # Placeholder para alinear

            st.divider()
            if st.button("🚀 COMENZAR SIMULACIÓN", type="primary", use_container_width=True):
                df = pd.read_excel(tema_sel, engine='openpyxl') if tema_sel.endswith('.xlsx') else pd.read_csv(tema_sel)
                if "Aleatorio" in modo:
                    st.session_state.current_df = df.sample(n=min(cantidad, len(df))).reset_index(drop=True)
                else:
                    st.session_state.current_df = df.iloc[offset : offset + cantidad].reset_index(drop=True)
                st.session_state.current_idx = 0
                st.session_state.quiz_step = 'playing'
                st.session_state.feedback = False
                st.session_state.feedback_shown = False
                st.session_state.tema_n = tema_sel
                st.rerun()
        else:
            st.warning("⚠️ No se han detectado archivos de estudio en el directorio.")

    elif st.session_state.quiz_step == 'playing':
        df = st.session_state.current_df
        idx = st.session_state.current_idx
        row = df.iloc[idx]
        
        # Header del Quiz mejorado
        st.markdown(f"""
            <div class="quiz-header">
                <div>📄 Módulo: {st.session_state.tema_n}</div>
                <div>Pregunta {idx+1} de {len(df)}</div>
            </div>
        """, unsafe_allow_html=True)
        st.progress((idx + 1) / len(df))
        
        st.markdown(f'<div class="question-box">{row["Pregunta"]}</div>', unsafe_allow_html=True)
        
        opc = [row['Respuesta 1'], row['Respuesta 2'], row['Respuesta 3'], row['Respuesta 4']]
        let = ['A', 'B', 'C', 'D']

        # Botones de respuesta
        if not st.session_state.feedback:
            for i, t in enumerate(opc):
                if pd.notna(t):
                    if st.button(f"{let[i]}. {t}", key=f"b_{i}"):
                        st.session_state.user_choice = let[i].lower()
                        st.session_state.feedback = True
                        st.rerun()
        
        # Lógica de Feedback y Resultado (solo si se ha respondido)
        if st.session_state.feedback:
            correcta = str(row['Respuesta']).strip().lower()
            es_acierto = st.session_state.user_choice == correcta
            
            # Registramos solo una vez por pregunta
            if not st.session_state.feedback_shown:
                 registrar_dato(st.session_state.tema_n, row['Pregunta'], "Acierto" if es_acierto else "Fallo")
                 st.session_state.feedback_shown = True

            # Tarjeta de resultado animada
            if es_acierto:
                st.markdown(f"""
                    <div class="result-card result-success">
                        <div class="result-icon">🎉</div>
                        <div class="result-text">¡Respuesta Correcta!<span>Has acertado la opción {correcta.upper()}. Sigue así.</span></div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                 st.markdown(f"""
                    <div class="result-card result-danger">
                        <div class="result-icon">⚠️</div>
                        <div class="result-text">Respuesta Incorrecta<span>La opción correcta era la <b>{correcta.upper()}</b>. Tu marcaste la {st.session_state.user_choice.upper()}.</span></div>
                    </div>
                """, unsafe_allow_html=True)

            st.write("") # Espaciador
            if st.button("Siguiente Pregunta ➡️", type="primary", use_container_width=True):
                if idx + 1 < len(df):
                    st.session_state.current_idx += 1
                    st.session_state.feedback = False
                    st.session_state.feedback_shown = False
                    st.rerun()
                else:
                    st.session_state.quiz_step = 'config'
                    st.balloons()
                    st.rerun()

# =========================================
# MODO 2: DASHBOARD ANALÍTICO
# =========================================
elif "Análisis" in app_mode:
    st.markdown('<div class="main-header">Cuadro de Mando Integral</div><p>Análisis de rendimiento en tiempo real.</p>', unsafe_allow_html=True)
    
    df_analytics = load_analysis_data()

    if df_analytics.empty or len(df_analytics) < 5:
        st.info("ℹ️ El sistema necesita más datos para generar un análisis fiable. Completa al menos 5 preguntas.")
    else:
        st.divider()
        # --- KPIs con estilo de tarjetas ---
        total = len(df_analytics)
        aciertos = df_analytics[df_analytics['resultado'] == 'Acierto'].shape[0]
        tasa = (aciertos / total * 100)

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.markdown(f'<div class="metric-card"><div class="metric-icon">📚</div><div class="metric-label">Preguntas Realizadas</div><div class="metric-value">{total}</div></div>', unsafe_allow_html=True)
        kpi2.markdown(f'<div class="metric-card"><div class="metric-icon">🎯</div><div class="metric-label">Aciertos Totales</div><div class="metric-value" style="color:{COLOR_SUCCESS};">{aciertos}</div></div>', unsafe_allow_html=True)
        kpi3.markdown(f'<div class="metric-card"><div class="metric-icon">📈</div><div class="metric-label">Tasa de Eficacia</div><div class="metric-value">{tasa:.0f}%</div></div>', unsafe_allow_html=True)

        # --- GRÁFICOS ---
        st.markdown('<div class="sub-header">Distribución del Rendimiento</div>', unsafe_allow_html=True)
        
        col_pie, col_bar = st.columns([1, 2])
        
        # Gráfico 1: Queso Global (Colores corporativos)
        with col_pie:
            fig_pie = px.pie(
                df_analytics, names='resultado', 
                title='Balance Global (Acierto/Fallo)',
                color='resultado',
                color_discrete_map={'Acierto': COLOR_SUCCESS, 'Fallo': COLOR_DANGER},
                hole=0.5
            )
            fig_pie.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
            fig_pie.update_traces(textinfo='percent+label', textfont_size=14)
            st.plotly_chart(fig_pie, use_container_width=True)

        # Gráfico 2: Barras Apiladas por Tema
        with col_bar:
            temas_group = df_analytics.groupby(['tema_corto', 'resultado']).size().reset_index(name='cantidad')
            fig_bar = px.bar(
                temas_group, x="cantidad", y="tema_corto", 
                color="resultado", title="Eficacia por Módulo Normativo",
                color_discrete_map={'Acierto': COLOR_SUCCESS, 'Fallo': COLOR_DANGER},
                barmode='stack', orientation='h'
            )
            fig_bar.update_layout(xaxis_title="Nº Preguntas", yaxis_title=None, margin=dict(t=40, b=0, l=0, r=0), legend_title=None)
            st.plotly_chart(fig_bar, use_container_width=True)

        # --- TABLA DE FALLOS ---
        st.markdown('<div class="sub-header">🚨 Áreas de Mejora Prioritarias (Top 5 Fallos)</div>', unsafe_allow_html=True)
        
        fallos_df = df_analytics[df_analytics['resultado'] == 'Fallo']
        if not fallos_df.empty:
            top_fallos = fallos_df['pregunta'].value_counts().reset_index().head(5)
            top_fallos.columns = ['Concepto / Pregunta', 'Frecuencia de Error']
            
            st.dataframe(
                top_fallos, use_container_width=True, hide_index=True,
                column_config={
                    "Concepto / Pregunta": st.column_config.TextColumn(width="large"),
                    "Frecuencia de Error": st.column_config.ProgressColumn(
                        format="%d ❌", min_value=0, max_value=top_fallos['Frecuencia de Error'].max(),
                        palette=["#fee2e2", COLOR_DANGER]
                    )
                }
            )
        else:
             st.markdown(f'<div style="background:{COLOR_SUCCESS}20; padding:20px; border-radius:10px; color:{COLOR_SUCCESS}; font-weight:600;">👏 ¡Enhorabuena! No hay registros de fallos recurrentes aún.</div>', unsafe_allow_html=True)
