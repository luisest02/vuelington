import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="VUELINGTON PRO", page_icon="✈️", layout="wide")

# ==========================================
# 🔐 GESTIÓN DE ESTADO (MEMORIA)
# ==========================================
# Esto soluciona el problema de que el botón de Telegram "no haga nada"
if 'resultados' not in st.session_state:
    st.session_state.resultados = []
if 'msg_telegram' not in st.session_state:
    st.session_state.msg_telegram = ""

# ==========================================
# 🔐 SECRETOS
# ==========================================
required_secrets = ["SERPAPI_KEY", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"]
missing = [s for s in required_secrets if s not in st.secrets]
if missing:
    st.error(f"🚨 FALTAN SECRETOS: {', '.join(missing)}")
    st.stop()

API_KEY = st.secrets["SERPAPI_KEY"]
TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
TG_ID = st.secrets["TELEGRAM_CHAT_ID"]

# ==========================================
# 📡 FUNCIONES
# ==========================================
def get_saldo_api():
    try:
        res = requests.get(f"https://serpapi.com/account?api_key={API_KEY}")
        data = res.json()
        return data.get("total_searches_left", "---")
    except: return "Error"

def enviar_telegram_debug(mensaje):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_ID, 
        "text": mensaje, 
        "parse_mode": "Markdown", 
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, data=payload)
        if r.status_code == 200:
            st.toast("✅ Mensaje enviado correctamente", icon="🚀")
        else:
            st.error(f"❌ Telegram rechazó el mensaje: {r.text}")
    except Exception as e:
        st.error(f"❌ Error de conexión con Telegram: {e}")

def buscar_vuelos(origen, region_code, f_ida, f_vuelta, precio_max, t_ida, t_vuelta):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "departure_id": origen,
        "outbound_date": f_ida,
        "return_date": f_vuelta,
        "currency": "EUR",
        "hl": "es",
        "api_key": API_KEY,
        "stops": "0",
        "type": "1",
        "outbound_times": t_ida,
        "return_times": t_vuelta
    }
    if region_code: params["arrival_id"] = region_code

    try:
        r = requests.get(url, params=params)
        data = r.json()
        
        if "error" in data:
            st.error(f"Error API: {data['error']}")
            return []
            
        raw = data.get("other_flights", []) + data.get("destinations", [])
        clean = []
        
        for v in raw:
            try:
                # Extracción precio
                p_val = 9999
                if "price" in v: p_val = v["price"]
                elif "flight_cost" in v: p_val = v["flight_cost"]
                
                # Seguridad si viene como texto
                if isinstance(p_val, str):
                    import re
                    d = re.findall(r'\d+', p_val)
                    if d: p_val = int(d[0])
                
                if p_val > precio_max: continue

                # Datos
                if "flights" in v:
                    seg = v["flights"][0]
                    dest = seg["arrival_airport"]["name"]
                    air = seg["airline"]
                    time = seg["departure_airport"]["time"]
                    # NUEVO LINK: Búsqueda directa en Google (Más fiable)
                    link = f"https://www.google.com/travel/flights?q=Flights%20to%20{dest}%20from%20MAD%20on%20{f_ida}%20returning%20{f_vuelta}"
                else:
                    dest = v.get("name", "Destino")
                    air = "Varios"
                    time = "N/A"
                    link = f"https://www.google.com/travel/flights?q=Flights%20to%20{dest}%20from%20MAD%20on%20{f_ida}%20returning%20{f_vuelta}"

                clean.append({
                    "destino": dest, "precio": p_val, 
                    "aerolinea": air, "hora": time, "link": link
                })
            except: continue
            
        clean.sort(key=lambda x: x['precio'])
        return clean
    except Exception as e:
        st.error(f"Error Python: {e}")
        return []

# ==========================================
# 🖥️ SIDEBAR (CONTROL)
# ==========================================
with st.sidebar:
    st.header("📊 Estado API")
    saldo = get_saldo_api()
    if saldo != "Error":
        st.metric("Llamadas Restantes", saldo)
        if isinstance(saldo, int) and saldo < 10:
            st.warning("⚠️ ¡Te quedan pocas!")
    else:
        st.error("Error conectando con SerpApi")

    st.divider()
    st.subheader("⚙️ Filtros")
    h_ida = st.slider("Salida V (desde)", 0, 23, 15, format="%dh")
    h_vuelta = st.slider("Vuelta D (desde)", 0, 23, 16, format="%dh")
    
    # Formato SerpApi
    str_ida = f"{h_ida},23"
    str_vuelta = f"{h_vuelta},23"

# ==========================================
# 🚀 INTERFAZ PRINCIPAL
# ==========================================
st.title("✈️ VUELINGTON PRO")

# --- LÓGICA DE FECHAS AUTOMÁTICAS ---
col_auto, col_man = st.columns([1, 3])

# Botón Mes Siguiente
if col_auto.button("📅 Buscar Mes Siguiente (+30d)", type="primary"):
    # Calcular fechas
    hoy = datetime.now()
    futuro = hoy + timedelta(days=30)
    # Ajustar al siguiente viernes
    dias_para_viernes = (4 - futuro.weekday() + 7) % 7
    v_futuro = futuro + timedelta(days=dias_para_viernes)
    d_futuro = v_futuro + timedelta(days=2)
    
    st.session_state.f_ida_default = v_futuro
    st.session_state.f_vuelta_default = d_futuro
    st.session_state.trigger_search = True # Gatillo para buscar
else:
    st.session_state.trigger_search = False

# Valores por defecto de los inputs
def_ida = st.session_state.get('f_ida_default', datetime.now() + timedelta(days=7))
def_vuelta = st.session_state.get('f_vuelta_default', datetime.now() + timedelta(days=9))

# Inputs Manuales
c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
with c1: f_ida_in = st.date_input("Ida", def_ida)
with c2: f_vuelta_in = st.date_input("Vuelta", def_vuelta)
with c3: region = st.selectbox("Destino", ["Europa", "Mundo Entero"])
with c4: presu = st.number_input("Max €", 50, 1000, 150, step=10)

# Gatillo de búsqueda (Manual o Automático)
if st.button("🔎 BUSCAR AHORA") or st.session_state.trigger_search:
    
    region_code = "/m/02j9z" if region == "Europa" else ""
    s_ida = f_ida_in.strftime('%Y-%m-%d')
    s_vuelta = f_vuelta_in.strftime('%Y-%m-%d')
    
    with st.spinner(f"Buscando para {s_ida}..."):
        # GUARDAMOS EN SESSION_STATE PARA QUE NO SE BORRE AL USAR TELEGRAM
        st.session_state.resultados = buscar_vuelos(
            "MAD", region_code, s_ida, s_vuelta, presu, str_ida, str_vuelta
        )
        
        # Preparamos mensaje de Telegram
        if st.session_state.resultados:
            msg = f"🚀 **VUELINGTON MANUAL**\n📅 {f_ida_in.strftime('%d/%b')} - {f_vuelta_in.strftime('%d/%b')}\n\n"
            for v in st.session_state.resultados[:10]:
                msg += f"✈️ {v['destino']}: **{v['precio']}€**\n🔗 [Ver en Google]({v['link']})\n\n"
            st.session_state.msg_telegram = msg
        else:
            st.session_state.msg_telegram = ""

# ==========================================
# 📝 MOSTRAR RESULTADOS (DESDE MEMORIA)
# ==========================================
if st.session_state.resultados:
    st.success(f"✅ {len(st.session_state.resultados)} vuelos encontrados")
    
    # Botón Telegram (Ahora funciona porque lee de memoria)
    if st.button("📱 Enviar Resultados a Telegram"):
        if st.session_state.msg_telegram:
            enviar_telegram_debug(st.session_state.msg_telegram)
        else:
            st.warning("No hay mensaje para enviar.")

    st.divider()
    
    # Renderizar Tarjetas
    for v in st.session_state.resultados:
        with st.container():
            k1, k2, k3 = st.columns([3, 2, 2])
            with k1:
                st.markdown(f"### {v['destino']}")
                st.caption(f"{v['aerolinea']} | {v['hora']}")
            with k2:
                st.markdown(f"### {v['precio']}€")
            with k3:
                st.link_button("Ver en Google Flights", v['link'])
            st.divider()

elif st.session_state.get('trigger_search') == False and st.button("Limpiar Resultados"):
    st.session_state.resultados = []
