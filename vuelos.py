import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="VUELINTON PRO", page_icon="✈️", layout="wide")

# --- LOGIN ---
if "PASSWORD_APP" in st.secrets:
    if "auth" not in st.session_state: st.session_state.auth = False
    
    if not st.session_state.auth:
        pwd = st.text_input("🔑 Contraseña", type="password")
        if pwd == st.secrets["PASSWORD_APP"]:
            st.session_state.auth = True
            st.rerun()
        st.stop()

# --- CONFIGURACIÓN DE LÍMITES (KPIs) ---
LIMITE_MENSUAL = 250  # O pon 100 si es tu plan
PETICIONES_BOT_SEMANALES = 13 # El bot hace 13 llamadas cada vez que corre
VECES_BOT_AL_MES = 4 # Corre 4 martes al mes

# --- CÁLCULO DE PRESUPUESTO ---
hoy_dia = datetime.now().day
semana_actual = (hoy_dia - 1) // 7 + 1
# Calculamos cuánto ha gastado el bot hasta hoy este mes
gasto_bot_estimado = semana_actual * PETICIONES_BOT_SEMANALES

if "contador_manual" not in st.session_state:
    st.session_state.contador_manual = 0

gasto_total = gasto_bot_estimado + st.session_state.contador_manual
restante = LIMITE_MENSUAL - gasto_total
porcentaje_uso = min(gasto_total / LIMITE_MENSUAL, 1.0)

# --- SIDEBAR DE CONTROL ---
with st.sidebar:
    st.title("📊 Estado API")
    st.progress(porcentaje_uso, text=f"{gasto_total}/{LIMITE_MENSUAL} Usados")
    
    if restante <= 0:
        st.error("⛔ ¡LÍMITE ALCANZADO!")
        bloqueo = True
    else:
        st.success(f"✅ Quedan ~{restante} búsquedas")
        st.caption(f"El bot automático consume ~{PETICIONES_BOT_SEMANALES*VECES_BOT_AL_MES} al mes.")
        bloqueo = False
    
    st.divider()
    st.write("Configuración Manual:")

# --- FUNCIÓN DE BÚSQUEDA ---
def buscar_google(origen, region, f_ida, f_vuelta, max_price):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "departure_id": origen,
        "arrival_id": region, # "Europe" o vacío para mundo
        "outbound_date": f_ida,
        "return_date": f_vuelta,
        "currency": "EUR",
        "hl": "es",
        "api_key": st.secrets["SERPAPI_KEY"],
        "stops": "0"
    }
    
    try:
        r = requests.get(url, params=params)
        if r.status_code == 200:
            return r.json().get("other_flights", [])
        elif r.status_code == 429:
            return "LIMIT"
        return []
    except:
        return []

# --- INTERFAZ PRINCIPAL ---
st.title("✈️ VUELINGTON EXPLORER")
st.markdown("Buscador manual optimizado. 1 Búsqueda = Múltiples destinos.")

col1, col2, col3 = st.columns(3)

with col1:
    f_ida = st.date_input("Ida", datetime.now() + timedelta(days=1))
with col2:
    f_vuelta = st.date_input("Vuelta", datetime.now() + timedelta(days=3))
with col3:
    # Selector de Región
    region_txt = st.selectbox("¿Dónde?", ["Europa (Recomendado)", "Mundo Entero"])
    region_code = "Europe" if "Europa" in region_txt else "Everywhere" 
    # Nota: En SerpApi, a veces para mundo es mejor no enviar arrival_id, pero "Everywhere" suele funcionar en engines modernos.

presupuesto = st.slider("Presupuesto Máximo", 50, 500, 150)

# Botón con bloqueo de seguridad
if st.button("🔎 BUSCAR CHOLLOS", disabled=bloqueo, type="primary"):
    # Incrementamos contador de sesión (visual)
    st.session_state.contador_manual += 1
    
    with st.spinner(f"Escaneando {region_txt}..."):
        # Ajuste para "Mundo Entero"
        destino_api = region_code
        if region_code == "Everywhere": destino_api = "" # Truco SerpApi: vacío = explorar
            
        data = buscar_google("MAD", destino_api, f_ida.strftime('%Y-%m-%d'), f_vuelta.strftime('%Y-%m-%d'), presupuesto)
        
        if data == "LIMIT":
            st.error("❌ La API ha rechazado la conexión (Límite real alcanzado).")
        elif not data:
            st.warning("No encontré vuelos por ese precio.")
        else:
            # Mostrar resultados
            resultados = []
            for v in data:
                try:
                    p = v.get("price", 9999)
                    if p <= presupuesto:
                        resultados.append({
                            "Ciudad": v["flights"][0]["arrival_airport"]["name"],
                            "Precio": f"{p}€",
                            "Aerolínea": v["flights"][0]["airline"],
                            "Hora Salida": v["flights"][0]["departure_airport"]["time"]
                        })
                except: pass
            
            if resultados:
                df = pd.DataFrame(resultados)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.success(f"Encontrados {len(resultados)} destinos.")
            else:
                st.info("Hay vuelos, pero todos superan tu presupuesto.")
