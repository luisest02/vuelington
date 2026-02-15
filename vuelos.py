import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="VUELINTON GOOGLE", page_icon="✈️")

# --- LOGIN SIMPLE ---
if "PASSWORD_APP" in st.secrets:
    pwd = st.text_input("Contraseña", type="password")
    if pwd != st.secrets["PASSWORD_APP"]:
        st.stop()

# --- FUNCIÓN BÚSQUEDA ---
def buscar_google(origen, f_ida, f_vuelta, max_price):
    # ¡Buscamos a TODA EUROPA para ahorrar peticiones!
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "departure_id": origen,
        "arrival_id": "Europe", # Truco maestro
        "outbound_date": f_ida,
        "return_date": f_vuelta,
        "currency": "EUR",
        "hl": "es",
        "api_key": st.secrets["SERPAPI_KEY"],
        "price_max": max_price,
        "stops": "0", # Directos
        "type": "1"
    }
    try:
        r = requests.get(url, params=params)
        if r.status_code == 200:
            return r.json().get("other_flights", [])
        return []
    except:
        return []

# --- INTERFAZ ---
st.title("✈️ Vuelington: Modo Explorador")
st.caption("Usando Google Flights (1 búsqueda = Todo Europa)")

col1, col2 = st.columns(2)
with col1:
    ida = st.date_input("Ida", datetime.now() + timedelta(days=1))
with col2:
    vuelta = st.date_input("Vuelta", datetime.now() + timedelta(days=3))

presupuesto = st.slider("Presupuesto Máx", 50, 300, 150)

if st.button("🔎 Buscar Chollos en Europa"):
    with st.spinner("Consultando a Google..."):
        # Formato fechas YYYY-MM-DD
        vuelos = buscar_google("MAD", ida.strftime('%Y-%m-%d'), vuelta.strftime('%Y-%m-%d'), presupuesto)
        
        if not vuelos:
            st.warning("No encontré nada o hubo un error.")
        else:
            for v in vuelos:
                try:
                    destino = v["flights"][0]["arrival_airport"]["name"]
                    precio = v.get("price", 0)
                    aerolinea = v["flights"][0]["airline"]
                    hora = v["flights"][0]["departure_airport"]["time"]
                    
                    # Filtro manual de precio por si acaso
                    if precio <= presupuesto:
                        st.success(f"{destino}")
                        st.markdown(f"**{precio}€** con {aerolinea}")
                        st.caption(f"Salida: {hora}")
                except:
                    pass
