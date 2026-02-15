import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="VUELINGTON PRO", page_icon="✈️", layout="wide")

# ==========================================
# 🔐 GESTIÓN DE SECRETOS
# ==========================================
if "SERPAPI_KEY" not in st.secrets:
    st.error("🚨 FALTA LA CLAVE: Añade 'SERPAPI_KEY' en los secretos de Streamlit.")
    st.stop()

API_KEY = st.secrets["SERPAPI_KEY"]

# Login simple
if "PASSWORD_APP" in st.secrets:
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        pwd = st.text_input("🔑 Contraseña", type="password")
        if pwd == st.secrets["PASSWORD_APP"]:
            st.session_state.auth = True
            st.rerun()
        st.stop()

# ==========================================
# ⚙️ CONFIGURACIÓN LATERAL
# ==========================================
with st.sidebar:
    st.header("🎛️ Filtros")
    
    # Selector de Horas
    activar_horas = st.toggle("Filtrar por Horario", value=True)
    
    str_ida = None
    str_vuelta = None
    
    if activar_horas:
        # Sliders de horas (0-23)
        h_ida = st.slider("Salida Viernes (desde)", 0, 23, 15, format="%dh")
        h_vuelta = st.slider("Vuelta Domingo (desde)", 0, 23, 16, format="%dh")
        
        # Formato SerpApi: "HHmm,2359"
        str_ida = f"{h_ida:02d}00,2359"
        str_vuelta = f"{h_vuelta:02d}00,2359"
    
    st.divider()
    
    if st.button("Verificar Saldo API"):
        try:
            res = requests.get(f"https://serpapi.com/account?api_key={API_KEY}")
            if res.status_code == 200:
                st.metric("Búsquedas restantes", res.json().get("total_searches_left", 0))
            else:
                st.error("Error de clave")
        except: st.error("Error conexión")

# ==========================================
# 🚀 FUNCIÓN BÚSQUEDA CORREGIDA
# ==========================================
def buscar_vuelos(origen, destino_id, f_ida, f_vuelta, precio_max, t_ida, t_vuelta):
    url = "https://serpapi.com/search"
    
    params = {
        "engine": "google_flights",
        "departure_id": origen,
        "outbound_date": f_ida,
        "return_date": f_vuelta,
        "currency": "EUR",
        "hl": "es", # Idioma español
        "api_key": API_KEY,
        "stops": "0", # Solo directos
        "type": "1"   # Ida y vuelta
    }

    # CORRECCIÓN IMPORTANTE: Si es Mundo Entero, NO mandamos arrival_id
    if destino_id:
        params["arrival_id"] = destino_id

    if precio_max:
        params["price_max"] = precio_max

    if t_ida and t_vuelta:
        params["outbound_times"] = t_ida
        params["return_times"] = t_vuelta

    try:
        r = requests.get(url, params=params)
        data = r.json()
        
        # Gestión de Errores de Google
        if "error" in data:
            st.error(f"❌ Google Error: {data['error']}")
            return []
            
        # Google devuelve los chollos genéricos en 'other_flights'
        # Si buscamos "Mundo Entero", a veces vienen en 'destinations'
        return data.get("other_flights", []) or data.get("destinations", [])

    except Exception as e:
        st.error(f"Error Python: {e}")
        return []

# ==========================================
# 🖥️ INTERFAZ PRINCIPAL
# ==========================================
st.title("✈️ VUELINGTON EXPLORER")
st.caption("Buscador de chollos manual.")

c1, c2, c3 = st.columns(3)
with c1: f_ida = st.date_input("Ida", datetime.now() + timedelta(days=5))
with c2: f_vuelta = st.date_input("Vuelta", datetime.now() + timedelta(days=7))
with c3:
    region_txt = st.selectbox("Destino", ["Europa", "Mundo Entero"])
    
    # ⚠️ AQUÍ ESTÁ EL FIX: CÓDIGOS REALES DE GOOGLE
    if region_txt == "Europa":
        region_code = "/m/02j9z" # Código interno de Google para Europa
    else:
        region_code = "" # Vacío para "Explore / Mundo"

presupuesto = st.slider("Presupuesto Máximo", 50, 500, 150)

if st.button("🔎 BUSCAR VUELOS", type="primary"):
    with st.spinner("Consultando Google Flights..."):
        vuelos = buscar_vuelos(
            "MAD", region_code, 
            f_ida.strftime('%Y-%m-%d'), 
            f_vuelta.strftime('%Y-%m-%d'), 
            presupuesto, str_ida, str_vuelta
        )
        
        if not vuelos:
            st.warning("No se encontraron vuelos baratos con estos filtros.")
        else:
            items = []
            for v in vuelos:
                try:
                    # Formato Lista de Vuelos
                    if "flights" in v:
                        seg = v["flights"][0]
                        items.append({
                            "Destino": seg["arrival_airport"]["name"],
                            "Precio": f"{v.get('price',0)}€",
                            "Aerolínea": seg["airline"],
                            "Salida": seg["departure_airport"]["time"],
                            "Link": f"https://www.google.com/travel/flights?tfs={seg['arrival_airport']['id']}" # Link simple
                        })
                    # Formato Mapa (Explore)
                    elif "name" in v and "flight_cost" in v:
                        items.append({
                            "Destino": v["name"],
                            "Precio": f"{v['flight_cost']}€",
                            "Aerolínea": "Varios",
                            "Salida": "Ver web",
                            "Link": "https://www.google.com/travel/flights"
                        })
                except: pass
            
            if items:
                st.success(f"✅ {len(items)} destinos encontrados")
                st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
