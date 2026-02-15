import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="VUELINTON PRO", page_icon="✈️", layout="wide")

# ==========================================
# 🔐 GESTIÓN DE SECRETOS (DEBUG)
# ==========================================
if "SERPAPI_KEY" not in st.secrets:
    st.error("🚨 ERROR CRÍTICO: No se encuentra 'SERPAPI_KEY' en los secretos.")
    st.info("Ve a 'Settings' > 'Secrets' en Streamlit Cloud y añade tu clave.")
    st.stop()

API_KEY = st.secrets["SERPAPI_KEY"]

# Login simple (Opcional)
if "PASSWORD_APP" in st.secrets:
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        pwd = st.text_input("🔑 Contraseña", type="password")
        if pwd == st.secrets["PASSWORD_APP"]:
            st.session_state.auth = True
            st.rerun()
        st.stop()

# ==========================================
# ⚙️ BARRA LATERAL (CONFIGURACIÓN)
# ==========================================
with st.sidebar:
    st.title("🎛️ Filtros Avanzados")
    
    st.markdown("### 🕒 Horarios Finde")
    usar_filtro_horas = st.checkbox("Activar Filtro Horario", value=True)
    
    str_ida = None
    str_vuelta = None
    
    if usar_filtro_horas:
        # Sliders para personalizar las horas
        h_ida = st.slider("Salida Viernes (desde)", 0, 23, 15, format="%dh")
        h_vuelta = st.slider("Vuelta Domingo (desde)", 0, 23, 17, format="%dh")
        
        # Formato exacto para SerpApi: "HHmm,2359"
        str_ida = f"{h_ida:02d}00,2359"
        str_vuelta = f"{h_vuelta:02d}00,2359"
        st.caption(f"Busca ida > {h_ida}:00 y vuelta > {h_vuelta}:00")
    else:
        st.caption("Buscando a cualquier hora del día")

    st.divider()
    
    # Botón para verificar saldo de la API
    if st.button("Verificar Saldo API"):
        try:
            info = requests.get(f"https://serpapi.com/account?api_key={API_KEY}").json()
            if "error" in info:
                st.error(f"Error clave: {info['error']}")
            else:
                total = info.get("total_searches_left", 0)
                st.metric("Búsquedas Restantes", total)
        except Exception as e:
            st.error(f"Error conectando: {e}")

# ==========================================
# 🚀 FUNCIÓN DE BÚSQUEDA
# ==========================================
def buscar_google_manual(origen, region_code, f_ida, f_vuelta, max_price, times_out, times_in):
    url = "https://serpapi.com/search"
    
    params = {
        "engine": "google_flights",
        "departure_id": origen,
        "outbound_date": f_ida,
        "return_date": f_vuelta,
        "currency": "EUR",
        "hl": "es",
        "api_key": API_KEY,
        "stops": "0", # Solo vuelos directos
        "type": "1"   # Ida y vuelta
    }

    # Si elegimos una región específica (Europa), la añadimos.
    # Si es "Everywhere" (Mundo), NO enviamos arrival_id para que Google sugiera.
    if region_code != "Everywhere":
        params["arrival_id"] = region_code

    if max_price:
        params["price_max"] = max_price

    # Aplicar filtros de hora solo si están definidos
    if times_out and times_in:
        params["outbound_times"] = times_out
        params["return_times"] = times_in

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        # Depuración de errores de la API
        if "error" in data:
            st.error(f"❌ Google Error: {data['error']}")
            return []
            
        # Intentamos extraer vuelos de las diferentes secciones que usa Google
        lista = data.get("other_flights", [])
        if not lista:
            lista = data.get("destinations", [])
            
        return lista

    except Exception as e:
        st.error(f"🔥 Error de conexión: {e}")
        return []

# ==========================================
# 🖥️ INTERFAZ PRINCIPAL
# ==========================================
st.title("✈️ VUELINGTON EXPLORER")
st.markdown("Buscador de chollos manual.")

col1, col2, col3 = st.columns(3)

with col1:
    f_ida = st.date_input("Fecha Ida", datetime.now() + timedelta(days=5)) # Por defecto prox viernes
with col2:
    f_vuelta = st.date_input("Fecha Vuelta", datetime.now() + timedelta(days=7)) # Por defecto prox domingo
with col3:
    region = st.selectbox("Destino", ["Europa", "Mundo Entero"])
    # Mapeo: Europa usa código 'Europe', Mundo usa código interno 'Everywhere'
    code_map = {"Europa": "Europe", "Mundo Entero": "Everywhere"}
    region_code = code_map[region]

presupuesto = st.slider("Presupuesto Máximo (€)", 50, 600, 150)

if st.button("🔎 BUSCAR VUELOS", type="primary"):
    with st.spinner(f"Buscando gangas en {region}..."):
        
        resultados = buscar_google_manual(
            "MAD", 
            region_code, 
            f_ida.strftime('%Y-%m-%d'), 
            f_vuelta.strftime('%Y-%m-%d'), 
            presupuesto,
            str_ida,    # Filtro hora ida
            str_vuelta  # Filtro hora vuelta
        )
        
        if not resultados:
            st.warning("⚠️ No se encontraron vuelos con estos filtros. Prueba a:")
            st.markdown("- Subir el presupuesto.")
            st.markdown("- Desactivar el filtro de horas en la barra lateral.")
            st.markdown("- Cambiar las fechas.")
        else:
            # Procesar datos para mostrar
            tabla = []
            for v in resultados:
                try:
                    # Caso 1: Estructura normal de vuelos
                    if "flights" in v:
                        seg = v["flights"][0]
                        precio = v.get("price", 0)
                        item = {
                            "Destino": seg["arrival_airport"]["name"],
                            "Precio": f"{precio}€",
                            "Aerolínea": seg["airline"],
                            "Hora Salida": seg["departure_airport"]["time"],
                            # Truco para enlace: Google Flights a veces no da URL directa
                            "Link": f"https://www.google.com/travel/flights?tfs={seg['arrival_airport']['id']}" 
                        }
                        tabla.append(item)
                    
                    # Caso 2: Estructura 'Explore' (Mapa)
                    elif "name" in v and "flight_cost" in v:
                        item = {
                            "Destino": v["name"],
                            "Precio": f"{v['flight_cost']}€",
                            "Aerolínea": "Varías",
                            "Hora Salida": "Consultar",
                            "Link": "https://www.google.com/travel/flights"
                        }
                        tabla.append(item)
                except:
                    continue

            if tabla:
                st.success(f"✅ ¡Encontrados {len(tabla)} destinos!")
                df = pd.DataFrame(tabla)
                st.dataframe(
                    df, 
                    column_config={"Link": st.column_config.LinkColumn("Ver en Google")},
                    use_container_width=True,
                    hide_index=True
                )
