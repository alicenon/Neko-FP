import streamlit as st
import pandas as pd
import urllib.parse
import os

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA
# ==============================================================================
st.set_page_config(page_title="Neko-FP Shannon 🐱", page_icon="🐱", layout="wide")

# Estilos CSS opcionales para refinar el diseño moderno
st.markdown("""
<style>
    /* Estilizamos un poco los contenedores simulando tarjetas modernas */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 10px;
        transition: box-shadow 0.3s ease-in-out;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    /* BALA DE PLATA FINAL: Ocultación por selectores de atributo parciales */
    #MainMenu, footer, .stAppDeployButton, [data-testid="stDecoration"], [data-testid="stStatusWidget"],
    [class^="viewerBadge"], [class*="viewerBadge"], 
    [data-testid="stViewerBadge"],
    div[class^="_container_gzau3"],
    a[href*="streamlit.io"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        height: 0 !important;
        width: 0 !important;
        pointer-events: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Mascota Kawaii en la Sidebar
try:
    # Buscamos la imagen generada (la más reciente que empiece por kawaii_neko)
    import glob
    mascot_path = glob.glob("kawaii_neko_mascot*.png")[0]
    st.sidebar.image(mascot_path, use_column_width=True)
except:
    st.sidebar.title("🐱 Neko-FP Shannon")

st.sidebar.markdown("### ✨ Tu Buscador de Ciclos")
st.sidebar.markdown("---")



# ==============================================================================
# LÓGICA DE DATOS (Fase Actual: Pandas -> Fase Futura: Azure SQL)
# ==============================================================================
# DISEÑO FUTURO PARA AZURE SQL:
# Cuando se mueva a producción con Azure SQL, esta lógica de pandas se 
# reemplazará. En lugar de cargar el archivo completo en memoria, se conectará 
# usando `pyodbc` o `SQLAlchemy` para traer solo los datos necesarios y delegar
# el filtrado a consultas SQL.
#
# EJEMPLO DE FUTURA CONEXIÓN:
# import pyodbc
# def get_db_connection():
#     conn_str = (
#         "Driver={ODBC Driver 18 for SQL Server};"
#         "Server=tcp:<servidor_azure>.database.windows.net,1433;"
#         "Database=<base_de_datos>;Uid=<usuario>;Pwd=<password>;"
#         "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
#     )
#     return pyodbc.connect(conn_str)
#
# def get_data_from_sql(municipio=None, modalidad=None, turno=None):
#     # Aquí construiríamos la Query dinámica basándonos en los filtros seleccionados
#     pass
# ==============================================================================

@st.cache_data
def load_data(file_path):
    """
    Función de carga inteligente (SEED).
    Para el prototipo usamos pandas leyendo el Excel con configuraciones específicas.
    """
    try:
        # FASE FUTURA AZURE SQL: 
        # df = pd.read_sql("SELECT * FROM OfertaFormativa", get_db_connection())
        # return df

        # Leemos el Excel sin asumir dónde está la cabecera
        df_raw = pd.read_excel(file_path, header=None)
        
        # Escaneamos las primeras 50 filas para encontrar los verdaderos títulos de las columnas
        header_idx = 0
        for i, row in df_raw.head(50).iterrows():
            row_text = ' '.join(row.dropna().astype(str).str.upper())
            if 'CENTRO' in row_text and ('MUNICIPIO' in row_text or 'FAMILIA' in row_text):
                header_idx = i
                break
                
        # Reconstruimos el DataFrame usando la fila correcta como nombres de columna
        df = df_raw.iloc[header_idx + 1:].copy()
        
        # Procesamos los nombres de columna de forma segura (evitando errores de float/utf-8)
        new_cols = []
        for c in df_raw.iloc[header_idx].values:
            c_str = str(c).strip() if pd.notna(c) else ""
            c_str = c_str.replace('.0', '').replace('Ã“', 'O').replace('Ó', 'O').upper()
            new_cols.append(c_str)
        df.columns = new_cols
        
        # IMPORTANTE: Excel usa "celdas combinadas". Al leerlas con Pandas, solo la primera fila tiene el valor, 
        # las demás son NaN. Usamos ffill (forward fill) para rellenar los datos de Centro, Municipio, etc. hacia abajo.
        cols_to_ffill = [col for col in df.columns if any(k in col for k in ['CENTRO', 'MUNICIPIO', 'FAMILIA', 'TITULARIDAD', 'CICLO', 'MODALIDAD'])]
        if cols_to_ffill:
            df[cols_to_ffill] = df[cols_to_ffill].ffill()
        
        # Aplicar el filtro de nulos exacto que se solicitó para limpiar filas completamente vacías al final
        # Usamos subset solo si existe la columna
        if 'CENTRO DOCENTE' in df.columns:
            # Eliminamos la fila solo si el CICLO y el CENTRO son nulos a la vez (por seguridad extra)
            df.dropna(subset=['CENTRO DOCENTE'], inplace=True)
        else:
            col_fallback = next((c for c in df.columns if 'CENTRO' in c), None)
            if col_fallback:
                df.dropna(subset=[col_fallback], inplace=True)
                
            
        return df
    except Exception as e:
        st.error(f"Error al procesar el archivo Excel: {e}")
        return None

# Detectamos archivos locales de Excel
excel_files = [f for f in os.listdir() if f.endswith('.xlsx')]

# Nombres amigables para los archivos y vista experimental
pretty_names = {
    "02_12_25_oferta_formativa_fp_virtual_25_26_superior Shannon.xlsx": "🌐 Oferta Formativa VIRTUAL",
    "familia de informatica para shannon_oferta_formativa_presencial.xlsx": "🏫 Oferta Formativa PRESENCIAL",
    "nearby": "📍 Centros CERCANOS A CASA (San Blas)"
}

if excel_files:
    # Añadimos la opción experimental al final
    options = excel_files + ["nearby"]
    file_to_load = st.sidebar.selectbox(
        "📂 Selecciona el Tipo de Oferta", 
        options,
        format_func=lambda x: pretty_names.get(x, x),
        key="main_file_selector"
    )
    
    # Botón para borrar filtros en la sidebar
    st.sidebar.write("---")
    if st.sidebar.button("🧹 Borrar Todos los Filtros", use_container_width=True):
        # Reiniciar todas las claves de filtros
        for key in ["search_box", "filter_acronimo", "filter_municipio", "filter_modalidad", "filter_turno", "filter_centro"]:
            if key in st.session_state:
                st.session_state[key] = "Todos" if "filter" in key else ""
        st.rerun()
        
    st.sidebar.write("---")
    if os.path.exists("kawaii_neko_mascot.png"):
        st.sidebar.image("kawaii_neko_mascot.png", caption="Neko-FP Shannon 🐾")
    else:
        st.sidebar.info("🐱 Neko-FP Shannon")
else:
    file_to_load = None

if file_to_load:
    # Si es la vista de cercanía, cargamos el archivo presencial para filtrar sobre él
    actual_file = "familia de informatica para shannon_oferta_formativa_presencial.xlsx" if file_to_load == "nearby" else file_to_load
    df = load_data(actual_file)
    
    if df is not None and not df.empty:
        is_nearby_view = (file_to_load == "nearby")
        
        # Título dinámico basado en la selección
        nombre_visual = pretty_names.get(file_to_load, "Oferta Formativa")
        st.title(f"🐱 Neko-FP Shannon: {nombre_visual}")
        
        if is_nearby_view:
            st.success("📍 **Modo Cercanía Activado:** Filtrando centros en San Blas y calculando tiempos desde vuestra casa.")
        else:
            st.info("ℹ️ **Nota para Shannon:** Actualmente solo se muestran **Centros Públicos** de Madrid. ¡Próximamente los privados!")
            
        st.markdown(f"Hola Shannon, aquí tienes los ciclos de la **{nombre_visual}**.")
        st.markdown("---")
        
        # Detectamos de manera segura las columnas aunque puedan tener ligeras variaciones
        col_centro = 'CENTRO DOCENTE' if 'CENTRO DOCENTE' in df.columns else next((c for c in df.columns if 'CENTRO' in str(c).upper()), None)
        col_municipio = 'MUNICIPIO' if 'MUNICIPIO' in df.columns else next((c for c in df.columns if 'MUNICIPIO' in str(c).upper()), None)
        col_modalidad = 'MODALIDAD' if 'MODALIDAD' in df.columns else next((c for c in df.columns if 'MODALIDAD' in str(c).upper()), None)
        col_turno = 'TURNO' if 'TURNO' in df.columns else next((c for c in df.columns if 'TURNO' in str(c).upper()), None)
        col_ciclo = 'CICLO FORMATIVO' if 'CICLO FORMATIVO' in df.columns else next((c for c in df.columns if 'CICLO' in str(c).upper()), None)
        col_familia = 'FAMILIA PROFESIONAL' if 'FAMILIA PROFESIONAL' in df.columns else next((c for c in df.columns if 'FAMILIA' in str(c).upper()), None)

        # 1. Filtro inicial para la vista de Cercanía (Experimental)
        if is_nearby_view:
            # Solo dejamos los centros que realmente están a un tiempo razonable
            keywords_cercanos = [
                "SUANZES", "GOMEZ-MORENO", "CASTRO", "QUEVEDO", 
                "BARAJAS", "ALAMEDA"
            ]
            pattern = "|".join(keywords_cercanos)
            df = df[df[col_centro].str.contains(pattern, case=False, na=False)]

        # ==============================================================================
        # INTERFAZ Y CONTROLES
        # ==============================================================================
        
        # Buscador de texto libre principal
        search_query = st.text_input("🔍 Buscar por palabra clave (Centro, Municipio, Ciclo...)", placeholder="Escribe aquí para buscar...", key="search_box")
        
        # Filtros Horizontales 
        c1, c2, c3, c4 = st.columns(4)
        
        filtered_df = df.copy()

        with c1:
            # Nuevo filtro por Especialidad/Acrónimo
            opciones_ciclo = ["Todos", "ASIR", "DAM", "DAW", "Doble Titulación"]
            selected_acronimo = st.selectbox("🎓 Especialidad", opciones_ciclo, key="filter_acronimo")
            if selected_acronimo != "Todos":
                mapeo_filtro = {
                    "ASIR": "Administración de Sistemas Informáticos en Red",
                    "DAM": "Desarrollo de Aplicaciones Multiplataforma",
                    "DAW": "Desarrollo de Aplicaciones Web",
                    "Doble Titulación": "doble titulación"
                }
                termino_filtro = mapeo_filtro[selected_acronimo]
                filtered_df = filtered_df[filtered_df[col_ciclo].str.contains(termino_filtro, case=False, na=False)]
        
        with c2:
            if col_municipio:
                municipios_lista = ["Todos"] + sorted(filtered_df[col_municipio].dropna().astype(str).unique().tolist())
                selected_municipio = st.selectbox("📍 Municipio", municipios_lista, key="filter_municipio")
                if selected_municipio != "Todos":
                    filtered_df = filtered_df[filtered_df[col_municipio] == selected_municipio]
                    
        with c3:
            if col_modalidad:
                modalidades_lista = ["Todos"] + sorted(filtered_df[col_modalidad].dropna().astype(str).unique().tolist())
                selected_modalidad = st.selectbox("📚 Modalidad", modalidades_lista, key="filter_modalidad")
                if selected_modalidad != "Todos":
                    filtered_df = filtered_df[filtered_df[col_modalidad] == selected_modalidad]
                    
        with c4:
            if col_turno:
                turnos_lista = ["Todos"] + sorted(filtered_df[col_turno].dropna().astype(str).unique().tolist())
                selected_turno = st.selectbox("⏰ Turno", turnos_lista, key="filter_turno")
                if selected_turno != "Todos":
                    filtered_df = filtered_df[filtered_df[col_turno] == selected_turno]
        
        # Segunda fila de filtros: Centro Específico
        if col_centro:
            centros_disponibles = ["Todos"] + sorted(filtered_df[col_centro].dropna().unique().tolist())
            selected_centro = st.selectbox("🏢 Filtrar por CENTRO DOCENTE ESPECÍFICO", centros_disponibles, key="filter_centro")
            if selected_centro != "Todos":
                filtered_df = filtered_df[filtered_df[col_centro] == selected_centro]
        
        # Aplicamos filtro de búsqueda inteligente con mapeo de acrónimos
        if search_query:
            query_clean = search_query.strip().upper()
            
            # Diccionario de equivalencias para que el usuario pueda usar acrónimos
            acronimos = {
                "ASIR": "Administración de Sistemas Informáticos en Red",
                "DAM": "Desarrollo de Aplicaciones Multiplataforma",
                "DAW": "Desarrollo de Aplicaciones Web"
            }
            
            if query_clean in acronimos:
                # Si el usuario escribe DAW, buscamos el nombre largo en la columna CICLO
                termino = acronimos[query_clean]
                filtered_df = filtered_df[filtered_df[col_ciclo].str.contains(termino, case=False, na=False)]
            else:
                # Búsqueda general (Centro, Municipio, etc.)
                mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)
                filtered_df = filtered_df[mask]

        st.caption(f"Se encontraron **{len(filtered_df)}** resultados.")
        st.markdown("---")
        
        # ==============================================================================
        # RENDERIZADO DE RESULTADOS: CUADRÍCULA DE TARJETAS (GRID)
        # ==============================================================================
        if filtered_df.empty:
            st.info("No hay resultados que coincidan con los filtros actuales.")
        else:
            # Definir cuántas tarjetas por fila queremos (3 funciona muy bien para layout="wide")
            cols_per_row = 3
            
            # Limitamos para evitar que se cuelgue el DOM si hay demasiados (paginación visual)
            max_results = 90
            display_df = filtered_df.head(max_results)
            
            if len(filtered_df) > max_results:
                st.warning(f"Mostrando los primeros {max_results} resultados. Por favor, usa los filtros para afinar la búsqueda.")
            
            # Recorremos de a grupos de a 3
            for i in range(0, len(display_df), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    if i + j < len(display_df):
                        row = display_df.iloc[i + j]
                        
                        # Cada contenedor es una tarjeta
                        with col:
                            with st.container(border=True):
                                # Extraemos valores básicos primero para usarlos en la lógica
                                centro_val = str(row[col_centro]) if col_centro and pd.notna(row[col_centro]) else "Centro Desconocido"
                                municipio_val = str(row[col_municipio]) if col_municipio and pd.notna(row[col_municipio]) else "N/A"
                                modalidad_val = str(row[col_modalidad]) if col_modalidad and pd.notna(row[col_modalidad]) else "N/A"
                                
                                # 1. Badge de Modalidad (Color dinámico modernizado)
                                badge_color = "#64748B" # Gris elegante (Slate)
                                if "VIRTUAL" in modalidad_val.upper() or "DISTANCIA" in modalidad_val.upper():
                                    badge_color = "#3B82F6" # Azul Real
                                elif "BILINGUE" in modalidad_val.upper():
                                    badge_color = "#F59E0B" # Dorado Bilingüe
                                elif "PRESENCIAL" in modalidad_val.upper() or "GENERAL" in modalidad_val.upper():
                                    badge_color = "#10B981" # Verde Esmeralda (General)
                                elif "SEMI" in modalidad_val.upper():
                                    badge_color = "#8B5CF6" # Violeta/Indigo
                                elif "INTENSIVA" in modalidad_val.upper():
                                    badge_color = "#F43F5E" # Rosa Fucsia
                                
                                # Lógica para el segundo Tag de Duración/Prácticas
                                duracion_text = ""
                                if "DOBLE" in modalidad_val.upper() and "INTENSIVA" in modalidad_val.upper():
                                    duracion_text = "⏱️ 2 AÑOS + 1 AÑO EN EMPRESA"
                                elif "INTENSIVA" in modalidad_val.upper():
                                    duracion_text = "⏱️ 1 AÑO + 1 AÑO EN EMPRESA"
                                else:
                                    duracion_text = "⏱️ 2 AÑOS (500H PRÁCTICAS)"
                                
                                # Lógica para el Tag de Cercanía (Solo en vista de centros cercanos)
                                dist_badge = ""
                                if is_nearby_view:
                                    # Mapeo de (Tiempo Real desde Lucas Mallada 16, Transporte)
                                    transporte = {
                                        "GOMEZ-MORENO": ("6 min", "🚶 Directo"),
                                        "CASTRO": ("8 min", "🚌 153 / 🚶 11 min"),
                                        "QUEVEDO": ("13-14 min", "🚌 4 ó 167/48/38"),
                                        "BARAJAS": ("24 min", "🚌 165 > 114"),
                                        "SUANZES": ("26 min", "🚌 153 / 🚶 30 min"),
                                        "ALAMEDA": ("29 min", "🚌 165 > 105")
                                    }
                                    nombre_c = centro_val.upper()
                                    info_t = next((v for k, v in transporte.items() if k in nombre_c), (None, None))
                                    if info_t[0]:
                                        tiempo, lineas = info_t
                                        dist_badge = f'<span style="background-color:#7C3AED; color:white; padding:4px 12px; border-radius:20px; font-size:10px; font-weight:bold;">🚶 {tiempo} ({lineas})</span>'
                                
                                # Generar URL de ruta en Google Maps (DISPONIBLE PARA TODAS LAS TARJETAS)
                                origen = "Calle de Lucas Mallada 16, Madrid"
                                destino = f"{centro_val}, Madrid"
                                maps_route_url = f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(origen)}&destination={urllib.parse.quote(destino)}&travelmode=transit"

                                # Renderizado de Badges en una fila
                                st.markdown(f'''
                                    <div style="display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 10px;">
                                        <span style="background-color:{badge_color}; color:white; padding:4px 12px; border-radius:20px; font-size:10px; font-weight:bold; text-transform:uppercase; letter-spacing:0.5px;">{modalidad_val}</span>
                                        <span style="background-color:#334155; color:white; padding:4px 12px; border-radius:20px; font-size:10px; font-weight:bold;">{duracion_text}</span>
                                        {dist_badge}
                                    </div>
                                ''', unsafe_allow_html=True)

                                # 2. Título del Ciclo Formativo
                                ciclo_val = str(row[col_ciclo]) if col_ciclo and pd.notna(row[col_ciclo]) else "Ciclo No Especificado"
                                st.markdown(f"### {ciclo_val}")
                                
                                # 3. Nombre del Centro Docente
                                st.markdown(f"**🏢 {centro_val}**")
                                
                                # 3. Etiquetas (Badges) simuladas
                                familia_val = str(row[col_familia]) if col_familia and pd.notna(row[col_familia]) else "N/A"
                                municipio_val = str(row[col_municipio]) if col_municipio and pd.notna(row[col_municipio]) else "N/A"
                                turno_val = str(row[col_turno]) if col_turno and pd.notna(row[col_turno]) else "N/A"
                                
                                # Mejora: Si es virtual y el turno es N/A, lo ponemos amigable
                                if ("VIRTUAL" in modalidad_val.upper() or "DISTANCIA" in modalidad_val.upper()) and turno_val == "N/A":
                                    turno_val = "Virtual / Flexible"
                                
                                # Renderizado vertical de los detalles para mantener el orden de la tarjeta
                                st.caption(f"💼 **Familia:** {familia_val}")
                                st.caption(f"📍 **Municipio:** {municipio_val}")
                                st.caption(f"⏰ **Turno:** {turno_val}")
                                
                                st.write("") # Espacio en blanco estructural
                                
                                # 4. Botones interactivos
                                if maps_route_url:
                                    st.link_button("📍 Ver Ruta desde Casa", url=maps_route_url, use_container_width=True)
                                
                                query_google = f"{centro_val} {municipio_val} enseñanzas"
                                google_url = f"https://www.google.com/search?q={urllib.parse.quote(query_google)}"
                                
                                st.link_button("🌐 Buscar Info del Centro", url=google_url, use_container_width=True)

else:
    st.info("⚠️ Sube un documento Excel válido desde la barra lateral o colócalo en el directorio del proyecto para comenzar.")
