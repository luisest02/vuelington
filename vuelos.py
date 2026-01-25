import streamlit as st
from amadeus import Client, ResponseError
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="EuroTrip Pro", page_icon="✈️", layout="wide")

# ==========================================
# 🔐 SISTEMA DE SEGURIDAD (PORTERO DIGITAL)
# ==========================================
def check_password():
    """Devuelve True si el usuario pone la contraseña correcta."""
    
    # Si no hay contraseña configurada en Secrets, dejamos pasar (Modo Inseguro)
    if "PASSWORD_APP" not in st.secrets:
        st.error("⚠️ Faltan configurar la contraseña en Secrets.")
        return False

    clave_secreta = st.secrets["PASSWORD_APP"]

    # Cuadro para meter la contraseña
    password_input = st.sidebar.text_input("🔒 Contraseña de Acceso", type="password")
    
    if password_input == clave_secreta:
        return True
    elif password_input == "":
        st.sidebar.warning("Introduce la contraseña.")
        return False
    else:
        st.sidebar.error("❌ Contraseña incorrecta")
        return False

# 🛑 SI LA CONTRASEÑA NO ES CORRECTA, PARAMOS TODO AQUÍ
if not check_password():
    st.title("🔒 Acceso Restringido")
    st.write("Por favor, introduce la contraseña en la barra lateral para usar EuroTrip Pro.")
    st.stop() # Detiene la ejecución del resto del código

# ==========================================
# 🚀 A PARTIR DE AQUÍ, SOLO ENTRA QUIEN SEPA LA CLAVE
# ==========================================

# --- GESTIÓN DE CREDENCIALES ---
try:
    API_KEY = st.secrets["AMADEUS_API_KEY"]
    API_SECRET = st.secrets["AMADEUS_API_SECRET"]
except FileNotFoundError:
    st.error("⚠️ Error: No se encontraron las claves API.")
    st.stop()

# --- DICCIONARIO AEROLÍNEAS ---
nombres_aerolineas = {
    "FR": "Ryanair", "U2": "EasyJet", "IB": "Iberia", "UX": "Air Europa",
    "VY": "Vueling", "HV": "Transavia", "W6": "Wizz Air", "LH": "Lufthansa",
    "AF": "Air France", "BA": "British Airways", "TP": "TAP Portugal",
    "LX": "Swiss", "AZ": "ITA Airways", "KL": "KLM", "D8": "Norwegian"
}

# --- BASE DE DATOS AEROPUERTOS ---
aeropuertos_europa = {
    "🇬🇧 Reino Unido": {"Londres": "LON", "Mánchester": "MAN", "Edimburgo": "EDI", "Bristol": "BRS"},
    "🇫🇷 Francia": {"París": "PAR", "Niza": "NCE", "Lyon": "LYS", "Burdeos": "BOD"},
    "🇮🇹 Italia": {"Roma": "ROM", "Milán": "MIL", "Venecia": "VCE", "Nápoles": "NAP", "Bolonia": "BLQ"},
    "🇩🇪 Alemania": {"Berlín": "BER", "Múnich": "MUC", "Frankfurt": "FRA", "Hamburgo": "HAM"},
    "🇪🇸 España": {"Mallorca": "PMI", "Ibiza": "IBZ", "Tenerife": "TCI", "Gran Canaria": "LPA"},
    "🇵🇹 Portugal": {"Lisboa": "LIS", "Oporto": "OPO", "Faro": "FAO", "Madeira": "FNC"},
    "🇳🇱 Benelux": {"Ámsterdam": "AMS", "Bruselas": "BRU", "Eindhoven": "EIN"},
    "🇪🇺 Este": {"Praga": "PRG", "Budapest": "BUD", "Varsovia": "WAW", "Cracovia": "KRK"},
    "❄️ Nórdicos": {"Copenhague": "CPH", "Estocolmo": "STO", "Oslo": "OSL"}
}

# Procesar nombres
catalogo_limpio = {}
ciudades_por_region = {}
for region, ciudades in aeropuertos_europa.items():
    lista_temp = []
    for nombre, codigo in ciudades.items():
        nom = f"{region.split()[0]} {nombre}"
        catalogo_limpio[nom] = codigo
        lista_temp.append(nom)
    ciudades_por_region[region] = lista_temp

# --- FUNCIÓN DE CACHÉ ---
@st.cache_data(ttl=3600, show_spinner=False)
def buscar_vuelos_api(origen, destino_code, f_ida, f_vuelta):
    try:
        amadeus = Client(client_id=API_KEY, client_secret=API_SECRET, hostname='production')
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origen, destinationLocationCode=destino_code,
            departureDate=f_ida, returnDate=f_vuelta,
            adults=1, currencyCode='EUR', max=20 
        )
        limpios = []
        for v in response.data:
            itin = v['itineraries']
            # Solo directos
            if len(itin[0]['segments']) == 1 and len(itin[1]['segments']) == 1:
                carrier = itin[0]['segments'][0]['carrierCode']
                limpios.append({
                    'precio': float(v['price']['total']),
                    'aerolinea': nombres_aerolineas.get(carrier, carrier),
                    'salida_ida': itin[0]['segments'][0]['departure']['at'],
                    'salida_vuelta': itin[1]['segments'][0]['departure']['at']
                })
        return limpios
    except ResponseError as e:
        if e.response.statusCode == 429: return "RATE_LIMIT"
        return []
    except: return []

def link_skyscanner(destino, f_ida, f_vuelta):
    fi = f_ida[2:].replace("-", "")
    fv = f_vuelta[2:].replace("-", "")
    return f"https://www.skyscanner.es/transport/flights/mad/{destino.lower()}/{fi}/{fv}/"

# --- INTERFAZ PRINCIPAL ---
st.title("🚀 EuroTrip Pro: Buscador Inteligente")

with st.sidebar:
    st.divider()
    st.header("⚙️ Configuración")
    
    fecha_inicio = st.date_input("¿Desde cuándo?", datetime.now())
    semanas = st.slider("Fines de semana a mirar", 1, 8, 4)
    dias_estancia = 2 if st.radio("Duración", ["V-D (2 días)", "V-S (1 día)"]) == "V-D (2 días)" else 1
    
    h_ida = st.slider("Salida Viernes >", 0, 23, 15, format="%dh")
    h_vuelta = st.slider("Regreso >", 0, 23, 16, format="%dh")

    # Selector de Destinos
    filtro = st.selectbox("Zona", ["Todas"] + list(aeropuertos_europa.keys()))
    opciones = []
    if filtro == "Todas":
        for l in ciudades_por_region.values(): opciones.extend(l)
        opciones.sort()
    else:
        opciones = ciudades_por_region[filtro]
    
    if filtro != "Todas" and st.button(f"Seleccionar todo {filtro}"):
        st.session_state['destinos'] = opciones

    destinos = st.multiselect("Destinos:", opciones, key='destinos')
    presupuesto = st.number_input("Presupuesto Máx (€)", 100, 2000, 150)
    buscar = st.button("🔎 RASTREAR VUELOS", type="primary")

if buscar:
    if not destinos: st.error("Selecciona destinos.")
    else:
        # Calcular fechas
        dias_v = (4 - fecha_inicio.weekday() + 7) % 7
        if dias_v == 0: dias_v = 0
        primer_v = fecha_inicio + timedelta(days=dias_v)
        
        fechas = []
        for i in range(semanas):
            ida = primer_v + timedelta(weeks=i)
            vuelta = ida + timedelta(days=dias_estancia)
            fechas.append((ida, vuelta))

        # Barra de progreso
        progreso = st.progress(0)
        total_ops = len(destinos) * len(fechas)
        contador = 0
        encontrados = 0

        for f_ida, f_vuelta in fechas:
            fi_str, fv_str = f_ida.strftime('%Y-%m-%d'), f_vuelta.strftime('%Y-%m-%d')
            
            with st.expander(f"🗓️ {f_ida.strftime('%d %b')} - {f_vuelta.strftime('%d %b')}", expanded=True):
                cols = st.columns(3)
                idx = 0
                hay = False
                
                for d_nombre in destinos:
                    contador += 1
                    progreso.progress(contador / total_ops)
                    
                    # Llamada API
                    d_code = catalogo_limpio[d_nombre]
                    res = buscar_vuelos_api('MAD', d_code, fi_str, fv_str)
                    
                    if res == "RATE_LIMIT": time.sleep(2)
                    elif res:
                        # Filtrar precio y hora
                        validos = []
                        for v in res:
                            ti = datetime.strptime(v['salida_ida'], "%Y-%m-%dT%H:%M:%S")
                            tv = datetime.strptime(v['salida_vuelta'], "%Y-%m-%dT%H:%M:%S")
                            if v['precio'] <= presupuesto and ti.hour >= h_ida and tv.hour >= h_vuelta:
                                validos.append({**v, 'hi': ti.strftime('%H:%M'), 'hv': tv.strftime('%H:%M')})
                        
                        validos.sort(key=lambda x: x['precio'])
                        
                        if validos:
                            top = validos[0]
                            with cols[idx%3]:
                                st.success(f"{d_nombre}")
                                st.metric(f"{top['aerolinea']}", f"{top['precio']} €")
                                st.caption(f"{top['hi']} - {top['hv']}")
                                st.link_button("Comprar", link_skyscanner(d_code, fi_str, fv_str))
                            idx += 1
                            hay = True
                            encontrados += 1
                
                if not hay: st.caption("Nada interesante.")

        if encontrados > 0: st.balloons()
