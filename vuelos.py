import streamlit as st
import requests
from datetime import datetime, timedelta

# Configuración de página más ancha y con icono
st.set_page_config(page_title="VUELINGTON PRO", page_icon="✈️", layout="wide")

# ==========================================
# 🎨 ESTILOS CSS (Para hacerlo bonito)
# ==========================================
st.markdown("""
<style>
    .flight-card {
        background-color: #262730;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #41444d;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .price-tag {
        font-size: 24px;
        font-weight: bold;
        color: #4CAF50;
    }
    .route-info {
        font-size: 18px;
        font-weight: 500;
    }
    .meta-info {
        color: #9da0a8;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 GESTIÓN DE ESTADO Y SECRETOS
# ==========================================
if 'resultados' not in st.session_state: st.session_state.resultados = []
if 'msg_telegram' not in st.session_state: st.session_state.msg_telegram = ""

# Verificación de claves
required = ["SERPAPI_KEY", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"]
missing = [s for s in required if s not in st.secrets]
if missing:
    st.error(f"🚨 FALTAN SECRETOS: {', '.join(missing)}")
    st.stop()

API_KEY = st.secrets["SERPAPI_KEY"]
TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
TG_ID = st.secrets["TELEGRAM_CHAT_ID"]

# ==========================================
# 🧠 LÓGICA DE NEGOCIO Y API
# ==========================================
def get_info_cuota():
    """Calcula el estado de la cuenta y el consumo del bot"""
    # ESTIMACIÓN DEL BOT:
    # Corre 1 vez a la semana (Martes)
    # Mira 13 semanas vista = 13 llamadas por ejecución
    # 13 llamadas x 4.3 semanas/mes = ~56 llamadas/mes
    CONSUMO_BOT_MENSUAL = 56 
    
    try:
        res = requests.get(f"https://serpapi.com/account?api_key={API_KEY}")
        data = res.json()
        total_left = data.get("total_searches_left", 0)
        
        # Cálculo de disponible real
        disponible_manual = total_left - CONSUMO_BOT_MENSUAL
        if disponible_manual < 0: disponible_manual = 0
        
        return {
            "total": total_left,
            "bot": CONSUMO_BOT_MENSUAL,
            "manual": disponible_manual,
            "status": "OK"
        }
    except:
        return {"status": "ERROR"}

def enviar_telegram_debug(mensaje):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_ID, "text": mensaje, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        requests.post(url, data=payload)
        st.toast("✅ Enviado al móvil", icon="📱")
    except Exception as e:
        st.error(f"Error Telegram: {e}")

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
        "stops": "0",       # Solo directos
        "type": "1",        # Ida y vuelta
        "outbound_times": t_ida, # Filtro hora ida
        "return_times": t_vuelta # Filtro hora vuelta
    }
    
    # Si es Europa, añadimos el ID. Si es Mundo, lo dejamos vacío.
    if region_code: params["arrival_id"] = region_code

    try:
        r = requests.get(url, params=params)
        data = r.json()
        
        if "error" in data:
            st.error(f"❌ Error API: {data['error']}")
            return []
            
        # Unimos las dos listas posibles donde Google pone los vuelos
        raw = data.get("other_flights", []) + data.get("destinations", [])
        
        if not raw:
            # Si la API devuelve 200 OK pero lista vacía, es que no hay vuelos
            st.warning("📡 La API conectó bien, pero Google dice que NO hay vuelos con esos filtros (Horario/Directo).")
            return []

        clean = []
        for v in raw:
            try:
                # 1. Extracción y Limpieza de Precio
                p_val = 9999
                if "price" in v: p_raw = v["price"]
                elif "flight_cost" in v: p_raw = v["flight_cost"]
                else: continue # Si no tiene precio, saltamos

                if isinstance(p_raw, int): p_val = p_raw
                elif isinstance(p_raw, str):
                    import re
                    # Extraer solo números de "150€" -> 150
                    nums = re.findall(r'\d+', p_raw)
                    if nums: p_val = int(nums[0])
                
                # 2. Filtro de Presupuesto (Python side)
                if p_val > precio_max: continue

                # 3. Datos del Vuelo
                if "flights" in v:
                    seg = v["flights"][0]
                    dest = seg["arrival_airport"]["name"]
                    air = seg["airline"]
                    time_out = seg["departure_airport"]["time"]
                    # Icono aerolínea
                    logo = seg.get("airline_logo", None)
                else:
                    dest = v.get("name", "Destino")
                    air = "Varios / N/A"
                    time_out = "Ver web"
                    logo = v.get("image", None)

                # 4. Generación de Link (Formato Búsqueda Google)
                # Esto abre Google Flights con los datos ya puestos
                link = f"https://www.google.com/travel/flights?q=Flights%20to%20{dest}%20from%20{origen}%20on%20{f_ida}%20returning%20{f_vuelta}"

                clean.append({
                    "destino": dest, "precio": p_val, 
                    "aerolinea": air, "hora": time_out, 
                    "link": link, "logo": logo
                })
            except Exception as e:
                continue
            
        clean.sort(key=lambda x: x['precio'])
        return clean

    except Exception as e:
        st.error(f"🔥 Error Crítico Python: {e}")
        return []

# ==========================================
# 🖥️ BARRA LATERAL (ESTADO DE CUENTA)
# ==========================================
with st.sidebar:
    st.header("📊 Tu Cuota API")
    
    info = get_info_cuota()
    
    if info["status"] == "OK":
        # Métricas visuales
        c1, c2 = st.columns(2)
        c1.metric("Total API", info['total'], help="Total búsquedas restantes en SerpApi")
        c2.metric("Reserva Bot", info['bot'], help="Lo que gastará el bot este mes (aprox)")
        
        st.divider()
        
        if info['manual'] > 10:
            st.success(f"✅ **{info['manual']}** disponibles para uso manual.")
        else:
            st.error(f"⚠️ **{info['manual']}** disponibles. ¡Ahorra!")
            
        st.caption("*El bot gasta ~13 llamadas cada martes.")
    else:
        st.error("Error conectando con SerpApi")

    st.divider()
    st.subheader("⚙️ Filtros Bot")
    st.info("Configurados: V(15h+) - D(16h+)")

# ==========================================
# 🚀 INTERFAZ PRINCIPAL
# ==========================================
st.title("✈️ VUELINGTON EXPLORER")
st.markdown("Busca chollos manualmente sin miedo a gastar de más.")

# --- ZONA DE CONTROL ---
with st.container(border=True):
    col_auto, col_dummy = st.columns([1, 2])
    if col_auto.button("📅 Cargar Mes Siguiente (+30d)", type="primary"):
        hoy = datetime.now()
        futuro = hoy + timedelta(days=30)
        dias_v = (4 - futuro.weekday() + 7) % 7
        v_fut = futuro + timedelta(days=dias_v)
        st.session_state.def_ida = v_fut
        st.session_state.def_vuelta = v_fut + timedelta(days=2)
        st.rerun()

    # Inputs
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    
    def_ida = st.session_state.get('def_ida', datetime.now() + timedelta(days=7))
    def_vuelta = st.session_state.get('def_vuelta', datetime.now() + timedelta(days=9))
    
    with c1: f_ida = st.date_input("Ida", def_ida)
    with c2: f_vuelta = st.date_input("Vuelta", def_vuelta)
    with c3: 
        region = st.selectbox("Destino", ["Europa (Recomendado)", "Mundo Entero"])
        region_code = "/m/02j9z" if "Europa" in region else ""
    with c4: presu = st.number_input("Max €", 50, 2000, 150, step=10)

    # Filtros avanzados (Expander para limpiar interfaz)
    with st.expander("🕒 Filtros de Horario (Viernes/Domingo)"):
        ch1, ch2 = st.columns(2)
        h_ida = ch1.slider("Salida Ida (Desde)", 0, 23, 14, format="%dh")
        h_vuelta = ch2.slider("Salida Vuelta (Desde)", 0, 23, 16, format="%dh")
        str_ida = f"{h_ida},23"
        str_vuelta = f"{h_vuelta},23"

    # BOTÓN BUSCAR
    if st.button("🔎 ESCANEAR CIELO", type="primary", use_container_width=True):
        s_ida = f_ida.strftime('%Y-%m-%d')
        s_vuelta = f_vuelta.strftime('%Y-%m-%d')
        
        with st.spinner("Conectando satélites... (Esto gasta 1 llamada API)"):
            st.session_state.resultados = buscar_vuelos(
                "MAD", region_code, s_ida, s_vuelta, presu, str_ida, str_vuelta
            )
            
            # Pre-generar mensaje Telegram
            if st.session_state.resultados:
                msg = f"🚀 **VUELINGTON MANUAL**\n📅 {f_ida.strftime('%d/%b')} - {f_vuelta.strftime('%d/%b')}\n\n"
                for v in st.session_state.resultados[:8]:
                    msg += f"✈️ {v['destino']}: **{v['precio']}€** ({v['aerolinea']})\n🔗 [Ver]({v['link']})\n\n"
                st.session_state.msg_telegram = msg

# ==========================================
# 🎫 RESULTADOS
# ==========================================
if st.session_state.resultados:
    st.divider()
    h1, h2 = st.columns([3, 1])
    h1.subheader(f"✅ {len(st.session_state.resultados)} Chollos Encontrados")
    
    if h2.button("📱 Enviar a Telegram"):
        enviar_telegram_debug(st.session_state.msg_telegram)

    # Renderizar tarjetas
    for v in st.session_state.resultados:
        # HTML/CSS Card
        logo_html = f'<img src="{v["logo"]}" height="30">' if v["logo"] else "✈️"
        
        with st.container():
            col_logo, col_info, col_price, col_btn = st.columns([1, 4, 2, 2])
            
            with col_logo:
                st.markdown(f"<div style='text-align:center; padding-top:10px;'>{logo_html}</div>", unsafe_allow_html=True)
            
            with col_info:
                st.markdown(f"**{v['destino']}**")
                st.caption(f"{v['aerolinea']} • Salida {v['hora']}")
            
            with col_price:
                st.markdown(f"<span style='color:#4CAF50; font-size:20px; font-weight:bold'>{v['precio']}€</span>", unsafe_allow_html=True)
            
            with col_btn:
                st.link_button("Ver Vuelo", v['link'], use_container_width=True)
            
            st.divider()

elif st.session_state.resultados == []:
    # Mensaje vacío (solo si se ha buscado antes, controlamos con flag si quisiéramos)
    pass
