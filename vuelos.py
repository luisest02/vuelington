import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="VUELINGTON PRO", page_icon="✈️", layout="wide")

# ==========================================
# 🔐 GESTIÓN DE SECRETOS
# ==========================================
required_secrets = ["SERPAPI_KEY", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"]
missing = [s for s in required_secrets if s not in st.secrets]

if missing:
    st.error(f"🚨 FALTAN SECRETOS: {', '.join(missing)}")
    st.info("Añádelos en Settings > Secrets")
    st.stop()

API_KEY = st.secrets["SERPAPI_KEY"]
TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
TG_ID = st.secrets["TELEGRAM_CHAT_ID"]

# Login (Opcional)
if "PASSWORD_APP" in st.secrets:
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        pwd = st.text_input("🔑 Contraseña", type="password")
        if pwd == st.secrets["PASSWORD_APP"]:
            st.session_state.auth = True
            st.rerun()
        st.stop()

# ==========================================
# 📡 FUNCIONES (API Y TELEGRAM)
# ==========================================
def enviar_a_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_ID, "text": mensaje, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        requests.post(url, data=payload)
        st.toast("✅ Enviado a Telegram", icon="📱")
    except Exception as e:
        st.error(f"Error enviando a Telegram: {e}")

def buscar_vuelos(origen, region_code, f_ida, f_vuelta, precio_max_usuario, t_ida, t_vuelta):
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

    # ID de destino (Europa o vacío para Mundo)
    if region_code:
        params["arrival_id"] = region_code

    # Nota: No enviamos price_max a la API porque Google lo ignora a veces.
    # Filtraremos nosotros manualmente después.

    try:
        r = requests.get(url, params=params)
        data = r.json()
        
        if "error" in data:
            st.error(f"❌ Google Error: {data['error']}")
            return []
            
        # Unificamos fuentes de datos
        raw_flights = data.get("other_flights", []) + data.get("destinations", [])
        
        vuelos_limpios = []
        
        for v in raw_flights:
            try:
                # Extracción de precio segura (quita el símbolo € y convierte a número)
                precio_num = 9999
                if "price" in v: precio_num = v["price"]
                elif "flight_cost" in v: precio_num = v["flight_cost"]
                
                # Gestión si el precio viene con texto (ej: "150€")
                if isinstance(precio_num, str):
                    import re
                    # Extraer solo dígitos
                    nums = re.findall(r'\d+', precio_num)
                    if nums: precio_num = int(nums[0])
                
                # 🔥 FILTRO ESTRICTO: Si pasa el presupuesto, ADIÓS.
                if precio_num > precio_max_usuario:
                    continue

                # Extracción de datos
                if "flights" in v:
                    seg = v["flights"][0]
                    destino = seg["arrival_airport"]["name"]
                    aerolinea = seg["airline"]
                    hora = seg["departure_airport"]["time"]
                    img = seg.get("airline_logo", None)
                    link = f"https://www.google.com/travel/flights?tfs={seg['arrival_airport']['id']}"
                else:
                    # Formato mapa
                    destino = v.get("name", "Destino")
                    aerolinea = "Varios"
                    hora = "N/A"
                    img = v.get("image", None)
                    link = "https://www.google.com/travel/flights"

                vuelos_limpios.append({
                    "destino": destino,
                    "precio": precio_num,
                    "aerolinea": aerolinea,
                    "hora": hora,
                    "img": img,
                    "link": link
                })

            except Exception as e:
                continue
        
        # Ordenar por precio (del más barato al más caro)
        vuelos_limpios.sort(key=lambda x: x['precio'])
        return vuelos_limpios

    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return []

# ==========================================
# 🖥️ INTERFAZ (UI MEJORADA)
# ==========================================
with st.sidebar:
    st.header("🎛️ Configuración")
    
    # Filtros Horarios
    st.subheader("🕒 Horarios (Finde)")
    h_ida = st.slider("Salida Viernes (desde)", 0, 23, 15, format="%dh")
    h_vuelta = st.slider("Vuelta Domingo (desde)", 0, 23, 16, format="%dh")
    
    str_ida = f"{h_ida},23"
    str_vuelta = f"{h_vuelta},23"
    
    st.info(f"Filtro: Viernes {h_ida}:00+ | Domingo {h_vuelta}:00+")
    
    st.divider()
    if st.button("Verificar Saldo API"):
        try:
            res = requests.get(f"https://serpapi.com/account?api_key={API_KEY}").json()
            st.metric("Búsquedas restantes", res.get("total_searches_left", "Error"))
        except: st.error("Error")

st.title("✈️ VUELINGTON PRO")
st.markdown("### Buscador de Chollos Manual")

# Layout de Búsqueda
c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
with c1: f_ida = st.date_input("Ida", datetime.now() + timedelta(days=5))
with c2: f_vuelta = st.date_input("Vuelta", datetime.now() + timedelta(days=7))
with c3:
    region = st.selectbox("Destino", ["Europa", "Mundo Entero"])
    region_code = "/m/02j9z" if region == "Europa" else ""
with c4:
    presupuesto = st.number_input("Max €", 50, 1000, 150, step=10)

if st.button("🔎 BUSCAR VUELOS", type="primary", use_container_width=True):
    with st.spinner("Escaneando cielos..."):
        resultados = buscar_vuelos(
            "MAD", region_code, 
            f_ida.strftime('%Y-%m-%d'), 
            f_vuelta.strftime('%Y-%m-%d'), 
            presupuesto, str_ida, str_vuelta
        )
        
        if not resultados:
            st.warning(f"🚫 No hay vuelos a {region} por menos de {presupuesto}€ con esos horarios.")
        else:
            st.balloons()
            
            # --- ZONA DE RESULTADOS ---
            st.success(f"✅ ¡Encontrados {len(resultados)} chollos!")
            
            # Botón para enviar TODO a Telegram
            msg_tg = f"🚀 **RESULTADOS MANUALES**\n📅 {f_ida.strftime('%d/%m')} - {f_vuelta.strftime('%d/%m')}\n\n"
            for v in resultados[:10]: # Top 10 para no saturar
                msg_tg += f"✈️ {v['destino']}: **{v['precio']}€** ({v['aerolinea']})\n🔗 [Ver Vuelo]({v['link']})\n\n"
            
            if st.button("📱 Enviar Top 10 a Telegram"):
                enviar_a_telegram(msg_tg)
            
            st.divider()

            # --- VISUALIZACIÓN EN TARJETAS ---
            for i, vuelo in enumerate(resultados):
                with st.container():
                    col_img, col_datos, col_precio = st.columns([1, 4, 2])
                    
                    with col_img:
                        # Si hay logo lo ponemos, si no un emoji
                        if vuelo['img']: st.image(vuelo['img'], width=50)
                        else: st.markdown("✈️")
                    
                    with col_datos:
                        st.markdown(f"**{vuelo['destino']}**")
                        st.caption(f"{vuelo['aerolinea']} | Salida: {vuelo['hora']}")
                    
                    with col_precio:
                        st.markdown(f"### {vuelo['precio']}€")
                        st.link_button("Comprar", vuelo['link'])
                    
                    st.divider()
