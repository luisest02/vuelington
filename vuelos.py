import streamlit as st
from amadeus import Client, ResponseError
from datetime import datetime, timedelta
import time
import requests
import os

st.set_page_config(page_title="VUELINTON", page_icon="✈️", layout="wide")

# --- SEGURIDAD ---
def check_password():
    if "PASSWORD_APP" not in st.secrets: return True
    clave = st.sidebar.text_input("🔒 Contraseña", type="password")
    if clave != st.secrets["PASSWORD_APP"]:
        st.sidebar.error("Acceso Bloqueado")
        st.stop()
    return True

check_password()

# --- CARGA CLAVES ---
try:
    API_KEY = st.secrets["AMADEUS_API_KEY"]
    API_SECRET = st.secrets["AMADEUS_API_SECRET"]
    TG_TOKEN = st.secrets.get("TELEGRAM_TOKEN", None)
    TG_ID = st.secrets.get("TELEGRAM_CHAT_ID", None)
except:
    st.error("❌ Faltan secretos.")
    st.stop()

# --- TELEGRAM ---
def enviar_a_telegram(texto):
    if not TG_TOKEN or not TG_ID:
        st.error("⚠️ Faltan secretos Telegram.")
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    # parse_mode='Markdown' activado para links
    payload = {"chat_id": TG_ID, "text": texto, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
        st.toast("✅ Enviado", icon="🚀")
    except:
        st.toast("❌ Error", icon="🔥")

# --- DATA ---
nombres_aerolineas = {
    "FR": "Ryanair", "U2": "EasyJet", "IB": "Iberia", "UX": "Air Europa",
    "VY": "Vueling", "HV": "Transavia", "W6": "Wizz Air", "LH": "Lufthansa",
    "AF": "Air France", "BA": "British Airways", "TP": "TAP Portugal",
    "LX": "Swiss", "AZ": "ITA Airways", "KL": "KLM", "D8": "Norwegian"
}

# 🌍 DICCIONARIO ACTUALIZADO (SIN ESPAÑA/PORTUGAL)
aeropuertos_europa = {
    "🇷🇴 Rumanía / 🇦🇱 Albania": {"Bucarest": "OTP", "Cluj-Napoca": "CLJ", "Tirana": "TIA"},
    "🇭🇷 Croacia / 🇧🇬 Bulgaria": {"Zagreb": "ZAG", "Dubrovnik": "DBV", "Sofía": "SOF"},
    "🇵🇱 Polonia / 🇭🇺 Hungría": {"Cracovia": "KRK", "Varsovia": "WAW", "Budapest": "BUD", "Praga": "PRG"},
    "🇮🇹 Italia": {"Roma": "ROM", "Milán": "MIL", "Venecia": "VCE", "Nápoles": "NAP", "Bolonia": "BLQ"},
    "🇬🇧 UK / 🇮🇪 Irlanda": {"Londres": "LON", "Dublín": "DUB", "Edimburgo": "EDI"},
    "🇫🇷 Francia": {"París": "PAR", "Niza": "NCE", "Lyon": "LYS"},
    "🇩🇪 Alemania": {"Berlín": "BER", "Múnich": "MUC", "Frankfurt": "FRA"},
    "🇳🇱 Benelux": {"Ámsterdam": "AMS", "Bruselas": "BRU"},
    "☀️ Malta": {"Malta": "MLA"}
}

catalogo_limpio = {}
ciudades_por_region = {}
for region, ciudades in aeropuertos_europa.items():
    l = []
    for k, v in ciudades.items():
        n = f"{region.split()[0]} {k}"
        catalogo_limpio[n] = v
        l.append(n)
    ciudades_por_region[region] = l

# --- API ---
@st.cache_data(ttl=3600, show_spinner=False)
def buscar_vuelos_api(origen, destino, f1, f2):
    try:
        # ⚠️ CAMBIA 'test' A 'production' CUANDO TENGAS CLAVES REALES
        amadeus = Client(client_id=API_KEY, client_secret=API_SECRET, hostname='test')
        res = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origen, destinationLocationCode=destino,
            departureDate=f1, returnDate=f2, adults=1, currencyCode='EUR', max=15)
        out = []
        for v in res.data:
            itin = v['itineraries']
            if len(itin[0]['segments'])==1 and len(itin[1]['segments'])==1:
                c = itin[0]['segments'][0]['carrierCode']
                out.append({
                    'precio': float(v['price']['total']),
                    'aerolinea': nombres_aerolineas.get(c, c),
                    'h_ida': itin[0]['segments'][0]['departure']['at'].split('T')[1][:5],
                    'h_vuelta': itin[1]['segments'][0]['departure']['at'].split('T')[1][:5]
                })
        return out
    except ResponseError as e:
        if e.response and e.response.status_code == 429: return "RATE_LIMIT"
        return []
    except: return []

def link_skyscanner(destino, f1, f2):
    # f1 y f2 vienen como YYYY-MM-DD
    # Skyscanner espera AAMMDD
    d_ida = f1[2:].replace('-', '')
    d_vuelta = f2[2:].replace('-', '')
    return f"https://www.skyscanner.es/transport/flights/mad/{destino.lower()}/{d_ida}/{d_vuelta}/"

# --- INTERFAZ ---
st.title("🚀 VUELINTON")

with st.sidebar:
    st.divider()
    f_ini = st.date_input("Inicio", datetime.now())
    semanas = st.slider("Semanas a mirar", 1, 8, 4)
    
    # SELECTOR DE TIPO DE VIAJE
    tipo_viaje = st.radio("Tipo de Escapada", ["Viernes - Domingo (2 noches)", "Sábado - Domingo (1 noche)"])
    
    st.divider()
    st.subheader("⏰ Horarios")
    txt_ida = "Salida Viernes >" if "Viernes" in tipo_viaje else "Salida Sábado >"
    
    h_ida_min = st.slider(txt_ida, 0, 23, 8 if "Sábado" in tipo_viaje else 15, format="%dh")
    h_vuelta_min = st.slider("Regreso Domingo >", 0, 23, 16, format="%dh")
    
    st.divider()
    presupuesto = st.number_input("Max €", 50, 2000, 150, step=10)
    
    zona = st.selectbox("Zona", ["Todas"] + list(aeropuertos_europa.keys()))
    ops = []
    if zona == "Todas":
        for l in ciudades_por_region.values(): ops.extend(l)
        ops.sort()
    else: ops = ciudades_por_region[zona]
    
    if zona != "Todas" and st.button("Seleccionar Todos"): st.session_state['dest'] = ops
    destinos = st.multiselect("Destinos", ops, key='dest')
    
    if st.button("🔎 BUSCAR", type="primary"):
        st.session_state['busqueda_activa'] = True

if st.session_state.get('busqueda_activa') and destinos:
    
    # Cálculo de fechas
    dia_v = (4 - f_ini.weekday() + 7) % 7
    if dia_v == 0: dia_v = 0
    primer_viernes = f_ini + timedelta(days=dia_v)
    
    fechas = []
    for i in range(semanas):
        base_viernes = primer_viernes + timedelta(weeks=i)
        
        if "Viernes" in tipo_viaje:
            ida = base_viernes
            vuelta = base_viernes + timedelta(days=2) # Domingo
            etiqueta = "V-D"
        else:
            ida = base_viernes + timedelta(days=1) # Sábado
            vuelta = base_viernes + timedelta(days=2) # Domingo
            etiqueta = "S-D"
            
        fechas.append((ida, vuelta, etiqueta))

    bar = st.progress(0)
    tot = len(destinos)*len(fechas)
    cnt = 0
    
    for fi, fv, tag in fechas:
        fi_s, fv_s = fi.strftime('%Y-%m-%d'), fv.strftime('%Y-%m-%d')
        fecha_display = f"{fi.strftime('%d/%b')} ({tag})"
        
        with st.expander(f"🗓️ {fecha_display}", expanded=True):
            cols = st.columns(3)
            idx = 0
            hay = False
            for ciu in destinos:
                cnt+=1
                bar.progress(cnt/tot)
                
                code = catalogo_limpio[ciu]
                data = buscar_vuelos_api('MAD', code, fi_s, fv_s)
                
                if data == "RATE_LIMIT": time.sleep(1)
                elif data:
                    # Filtros manuales
                    validos = []
                    for x in data:
                        hi = int(x['h_ida'].split(':')[0])
                        hv = int(x['h_vuelta'].split(':')[0])
                        if x['precio'] <= presupuesto and hi >= h_ida_min and hv >= h_vuelta_min:
                            validos.append(x)
                            
                    validos.sort(key=lambda x: x['precio'])
                    
                    if validos:
                        top = validos[0]
                        with cols[idx%3]:
                            st.info(f"{ciu}")
                            st.metric(top['aerolinea'], f"{top['precio']}€")
                            st.caption(f"{top['h_ida']} - {top['h_vuelta']}")
                            
                            c1, c2 = st.columns(2)
                            url_sky = link_skyscanner(code, fi_s, fv_s)
                            
                            with c1:
                                st.link_button("✈️", url_sky)
                            with c2:
                                # MODIFICADO: Mensaje Telegram con link oculto en el nombre
                                msg_tg = f"🔥 **MANUAL ({tag})**\n✈️ Madrid -> [{ciu}]({url_sky})\n💰 **{top['precio']}€**\n📅 {fi.strftime('%d/%m')} - {fv.strftime('%d/%m')}\n🕓 {top['h_ida']} - {top['h_vuelta']}"
                                if st.button("📱", key=f"tg_{ciu}_{fi_s}"):
                                    enviar_a_telegram(msg_tg)
                        idx+=1
                        hay=True
            if not hay: st.caption("🚫 Nada")
    bar.empty()
