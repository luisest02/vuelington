import streamlit as st
from amadeus import Client, ResponseError
from datetime import datetime, timedelta
import time
import requests # <--- NECESARIO PARA TELEGRAM
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="VUELINTON", page_icon="✈️", layout="wide")

# ==========================================
# 🔐 SEGURIDAD: PORTERO Y CREDENCIALES
# ==========================================
def check_password():
    if "PASSWORD_APP" not in st.secrets: return True # Si no hay clave configurada, pasa (modo dev)
    clave = st.sidebar.text_input("🔒 Contraseña", type="password")
    if clave != st.secrets["PASSWORD_APP"]:
        st.sidebar.error("Acceso Bloqueado")
        st.stop()
    return True

check_password() # Ejecutamos el portero

# Cargar Claves
try:
    API_KEY = st.secrets["AMADEUS_API_KEY"]
    API_SECRET = st.secrets["AMADEUS_API_SECRET"]
    # Intentamos cargar Telegram (Opcional, para que no falle si no los has puesto aún)
    TG_TOKEN = st.secrets.get("TELEGRAM_TOKEN", None)
    TG_ID = st.secrets.get("TELEGRAM_CHAT_ID", None)
except:
    st.error("Faltan secretos de configuración.")
    st.stop()

# ==========================================
# 📨 FUNCIÓN ENVIAR A TELEGRAM
# ==========================================
def enviar_a_telegram(texto):
    if not TG_TOKEN or not TG_ID:
        st.toast("⚠️ Configura los secretos de Telegram para usar esta función.", icon="⚠️")
        return
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_ID, "text": texto, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
        st.toast("✅ ¡Enviado a tu móvil!", icon="🚀")
    except:
        st.toast("❌ Error al enviar.", icon="🔥")

# ... (DICCIONARIOS Y FUNCIONES AUXILIARES IGUAL QUE ANTES) ...
nombres_aerolineas = {
    "FR": "Ryanair", "U2": "EasyJet", "IB": "Iberia", "UX": "Air Europa",
    "VY": "Vueling", "HV": "Transavia", "W6": "Wizz Air", "LH": "Lufthansa",
    "AF": "Air France", "BA": "British Airways", "TP": "TAP Portugal",
    "LX": "Swiss", "AZ": "ITA Airways", "KL": "KLM", "D8": "Norwegian"
}

aeropuertos_europa = {
    "🇬🇧 Reino Unido": {"Londres": "LON", "Mánchester": "MAN", "Edimburgo": "EDI"},
    "🇫🇷 Francia": {"París": "PAR", "Niza": "NCE", "Lyon": "LYS"},
    "🇮🇹 Italia": {"Roma": "ROM", "Milán": "MIL", "Venecia": "VCE", "Nápoles": "NAP"},
    "🇩🇪 Alemania": {"Berlín": "BER", "Múnich": "MUC", "Frankfurt": "FRA"},
    "🇪🇸 España": {"Mallorca": "PMI", "Ibiza": "IBZ", "Tenerife": "TCI", "Gran Canaria": "LPA"},
    "🇵🇹 Portugal": {"Lisboa": "LIS", "Oporto": "OPO", "Faro": "FAO"},
    "🇳🇱 Benelux": {"Ámsterdam": "AMS", "Bruselas": "BRU"},
    "🇪🇺 Este": {"Praga": "PRG", "Budapest": "BUD", "Varsovia": "WAW"},
    "❄️ Nórdicos": {"Copenhague": "CPH", "Estocolmo": "STO", "Oslo": "OSL"}
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

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_vuelos_api(origen, destino, f1, f2):
    try:
        amadeus = Client(client_id=API_KEY, client_secret=API_SECRET, hostname='production')
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
    except ResponseError as e: return "RATE_LIMIT" if e.response.statusCode==429 else []
    except: return []

def link_skyscanner(destino, f1, f2):
    return f"https://www.skyscanner.es/transport/flights/mad/{destino.lower()}/{f1[2:].replace('-','')}/{f2[2:].replace('-','')}/"

# --- INTERFAZ ---
st.title("🚀 EuroTrip Pro")

with st.sidebar:
    st.divider()
    f_ini = st.date_input("Inicio", datetime.now())
    semanas = st.slider("Semanas", 1, 8, 4)
    dias = 2 if st.radio("Duración", ["2 días (V-D)", "1 día (V-S)"]) == "2 días (V-D)" else 1
    presupuesto = st.number_input("Max €", 50, 2000, 150)
    
    zona = st.selectbox("Zona", ["Todas"] + list(aeropuertos_europa.keys()))
    ops = []
    if zona == "Todas":
        for l in ciudades_por_region.values(): ops.extend(l)
        ops.sort()
    else: ops = ciudades_por_region[zona]
    
    if zona != "Todas" and st.button("Seleccionar Todos"): st.session_state['dest'] = ops
    destinos = st.multiselect("Destinos", ops, key='dest')
    buscar = st.button("🔎 BUSCAR", type="primary")

if buscar and destinos:
    dia_v = (4 - f_ini.weekday() + 7) % 7
    if dia_v == 0: dia_v = 0
    viernes_1 = f_ini + timedelta(days=dia_v)
    
    fechas = []
    for i in range(semanas):
        ida = viernes_1 + timedelta(weeks=i)
        vuelta = ida + timedelta(days=dias)
        fechas.append((ida, vuelta))

    bar = st.progress(0)
    tot = len(destinos)*len(fechas)
    cnt = 0
    
    for fi, fv in fechas:
        fi_s, fv_s = fi.strftime('%Y-%m-%d'), fv.strftime('%Y-%m-%d')
        with st.expander(f"🗓️ {fi.strftime('%d/%b')} - {fv.strftime('%d/%b')}", expanded=True):
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
                    validos = [x for x in data if x['precio'] <= presupuesto]
                    validos.sort(key=lambda x: x['precio'])
                    if validos:
                        top = validos[0]
                        with cols[idx%3]:
                            st.info(f"{ciu}")
                            st.metric(top['aerolinea'], f"{top['precio']}€")
                            st.caption(f"{top['h_ida']} - {top['h_vuelta']}")
                            
                            # --- BOTONES DE ACCIÓN ---
                            c1, c2 = st.columns(2)
                            with c1:
                                st.link_button("✈️", link_skyscanner(code, fi_s, fv_s))
                            with c2:
                                # EL BOTÓN MÁGICO PARA ENVIAR A TELEGRAM
                                msg_tg = f"🔥 **BÚSQUEDA MANUAL**\n✈️ Madrid -> {ciu}\n💰 **{top['precio']}€**\n📅 {fi.strftime('%d/%m')} - {fv.strftime('%d/%m')}\n🕓 {top['h_ida']} - {top['h_vuelta']}"
                                if st.button("📱", key=f"tg_{ciu}_{fi_s}"):
                                    enviar_a_telegram(msg_tg)
                            
                        idx+=1
                        hay=True
            if not hay: st.caption("🚫")
