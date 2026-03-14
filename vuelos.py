import streamlit as st
import requests
from datetime import datetime, timedelta
import re

# ==========================================
# 1. Configuración de página (Debe ser la primera instrucción)
# ==========================================
st.set_page_config(page_title="VUELINGTON PRO", page_icon="✈️", layout="wide")

# ==========================================
# 2. 🎨 ESTILOS CSS
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
# 3. 🔐 GESTIÓN DE ESTADO Y SECRETOS (Seguridad)
# ==========================================
if 'resultados' not in st.session_state: st.session_state.resultados = []
if 'msg_telegram' not in st.session_state: st.session_state.msg_telegram = ""

# Verificación de claves seguras
required = ["SERPAPI_KEY", "TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID"]
missing = [s for s in required if s not in st.secrets]
if missing:
    st.error(f"🚨 FALTAN SECRETOS: {', '.join(missing)}. Configúralos en Streamlit Cloud o en .streamlit/secrets.toml")
    st.stop()

API_KEY = st.secrets["SERPAPI_KEY"]
TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
TG_ID = st.secrets["TELEGRAM_CHAT_ID"]

# ==========================================
# 4. 🧠 LÓGICA DE NEGOCIO Y API
# ==========================================
def get_info_cuota():
    """Calcula el estado de la cuenta y el consumo del bot"""
    CONSUMO_BOT_MENSUAL = 48 # Actualizado a las 12 semanas que busca ahora el bot
    
    try:
        res = requests.get(f"https://serpapi.com/account?api_key={API_KEY}", timeout=10)
        data = res.json()
        total_left = data.get("total_searches_left", 0)
        
        disponible_manual = max(0, total_left - CONSUMO_BOT_MENSUAL)
        
        return {
            "total": total_left,
            "bot": CONSUMO_BOT_MENSUAL,
            "manual": disponible_manual,
            "status": "OK"
        }
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}

def enviar_telegram_debug(mensaje):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_ID, "text": mensaje, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try:
        # CORRECCIÓN DE SEGURIDAD Y ESTABILIDAD: json=payload
        requests.post(url, json=payload, timeout=10)
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
        "type": "1",        # FORZAR IDA Y VUELTA
        "outbound_times": t_ida,
        "return_times": t_vuelta
    }
    
    if region_code: params["arrival_id"] = region_code

    try:
        r = requests.get(url, params=params, timeout=20)
        data = r.json()
        
        if "error" in data:
            st.error(f"❌ Error API: {data['error']}")
            return []
            
        raw = data.get("best_flights", []) + data.get("other_flights", []) + data.get("destinations", [])
        
        if not raw:
            st.warning("📡 Google no devolvió vuelos con esos filtros. Prueba a subir el precio o ampliar las horas.")
            return []

        clean = []
        for v in raw:
            try:
                p_val = 9999
                p_raw = v.get("price", v.get("flight_cost"))
                
                if isinstance(p_raw, int): 
                    p_val = p_raw
                elif isinstance(p_raw, str):
                    nums = re.findall(r'\d+', p_raw)
                    if nums: p_val = int(nums[0])
                
                if p_val > precio_max: continue

                if "flights" in v:
                    seg = v["flights"][0]
                    dest = seg["arrival_airport"]["name"]
                    air = seg["airline"]
                    time_out = seg["departure_airport"]["time"]
                    logo = seg.get("airline_logo", None)
                else:
                    dest = v.get("name", "Destino")
                    air = "Varios / N/A"
                    time_out = "Ver web"
                    logo = v.get("image", None)

                link = f"https://www.google.com/travel/flights?q=Flights%20to%20{dest}%20from%20{origen}%20on%20{f_ida}%20returning%20{f_vuelta}"

                clean.append({
                    "destino": dest, "precio": p_val, 
                    "aerolinea": air, "hora": time_out, 
                    "link": link, "logo": logo
                })
            except Exception:
                continue
            
        clean.sort(key=lambda x: x['precio'])
        return clean

    except Exception as e:
        st.error(f"🔥 Error Crítico Python: {e}")
        return []

# ==========================================
# 5. 🖥️ BARRA LATERAL
# ==========================================
with st.sidebar:
    st.header("📊 Tu Cuota API")
    info = get_info_cuota()
    
    if info["status"] == "OK":
        c1, c2 = st.columns(2)
        c1.metric("Total API", info['total'])
        c2.metric("Reserva Bot", info['bot'])
        st.divider()
        if info['manual'] > 10:
            st.success(f"✅ **{info['manual']}** disponibles manual.")
        else:
            st.error(f"⚠️ **{info['manual']}** disponibles.")
    else:
        st.error("Error conectando con SerpApi")

# ==========================================
# 6. 🚀 INTERFAZ PRINCIPAL Y ZONA DE CONTROL
# ==========================================
st.title("✈️ VUELINGTON EXPLORER")
st.markdown("Busca chollos manualmente sin miedo a gastar de más.")

with st.container(border=True):
    col_auto1, col_auto2, col_dummy = st.columns([1, 1, 2])
    
    if col_auto1.button("📅 Mes Siguiente (+30d)", type="secondary"):
        hoy = datetime.now()
        futuro = hoy + timedelta(days=30)
        dias_v = (4 - futuro.weekday() + 7) % 7
        v_fut = futuro + timedelta(days=dias_v)
        st.session_state.def_ida = v_fut
        st.session_state.def_vuelta = v_fut + timedelta(days=2)
        st.rerun()

    if col_auto2.button("⚡ Próximo Finde (Sáb-Dom)", type="primary"):
        hoy = datetime.now()
        dias_sabado = (5 - hoy.weekday() + 7) % 7
        if dias_sabado == 0: dias_sabado = 7
        sabado_prox = hoy + timedelta(days=dias_sabado)
        
        st.session_state.def_ida = sabado_prox
        st.session_state.def_vuelta = sabado_prox + timedelta(days=1)
        st.rerun()

    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    
    def_ida = st.session_state.get('def_ida', datetime.now() + timedelta(days=7))
    def_vuelta = st.session_state.get('def_vuelta', datetime.now() + timedelta(days=8))
    
    with c1: f_ida = st.date_input("Ida", def_ida)
    with c2: f_vuelta = st.date_input("Vuelta", def_vuelta)
    with c3: 
        region = st.selectbox("Destino", ["Europa (Recomendado)", "Mundo Entero"])
        region_code = "/m/02j9z" if "Europa" in region else ""
    with c4: presu = st.number_input("Max €", 50, 2000, 150, step=10)

    with st.expander("🕒 Filtros de Horario (Salida y Regreso)", expanded=True):
        ch1, ch2 = st.columns(2)
        h_ida = ch1.slider("Salida Ida (Hasta las)", 0, 23, 12, format="%dh") 
        h_vuelta = ch2.slider("Salida Vuelta (Desde las)", 0, 23, 16, format="%dh")
        
        str_ida = f"05,{h_ida}" 
        str_vuelta = f"{h_vuelta},23"

    if st.button("🔎 ESCANEAR CIELO", type="primary", use_container_width=True):
        s_ida = f_ida.strftime('%Y-%m-%d')
        s_vuelta = f_vuelta.strftime('%Y-%m-%d')
        
        with st.spinner("Conectando satélites... (Esto gasta 1 llamada API)"):
            st.session_state.resultados = buscar_vuelos(
                "MAD", region_code, s_ida, s_vuelta, presu, str_ida, str_vuelta
            )
            
            if st.session_state.resultados:
                msg = f"🚀 **VUELINGTON MANUAL**\n📅 {f_ida.strftime('%d/%b')} - {f_vuelta.strftime('%d/%b')}\n\n"
                for v in st.session_state.resultados[:8]:
                    msg += f"✈️ {v['destino']}: **{v['precio']}€** ({v['aerolinea']})\n🔗 [Ver]({v['link']})\n\n"
                st.session_state.msg_telegram = msg

# ==========================================
# 7. 🎫 RESULTADOS
# ==========================================
if st.session_state.resultados:
    st.divider()
    h1, h2 = st.columns([3, 1])
    h1.subheader(f"✅ {len(st.session_state.resultados)} Chollos Encontrados")
    
    if h2.button("📱 Enviar a Telegram"):
        enviar_telegram_debug(st.session_state.msg_telegram)

    for v in st.session_state.resultados:
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
