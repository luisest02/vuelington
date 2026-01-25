import streamlit as st
from amadeus import Client, ResponseError
from datetime import datetime, timedelta
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="EuroTrip Pro", page_icon="✈️", layout="wide")

# --- 🔒 GESTIÓN DE CREDENCIALES SEGURA ---
# Esto busca las claves en los "Secrets" de Streamlit Cloud.
# Si no las encuentra, muestra un aviso amigable.
try:
    API_KEY = st.secrets["AMADEUS_API_KEY"]
    API_SECRET = st.secrets["AMADEUS_API_SECRET"]
except FileNotFoundError:
    st.error("⚠️ Error: No se encontraron las claves API. Configura los 'Secrets' en Streamlit Cloud.")
    st.stop()

# --- DICCIONARIO DE AEROLÍNEAS ---
nombres_aerolineas = {
    "FR": "Ryanair", "U2": "EasyJet", "IB": "Iberia", "UX": "Air Europa",
    "VY": "Vueling", "HV": "Transavia", "W6": "Wizz Air", "LH": "Lufthansa",
    "AF": "Air France", "BA": "British Airways", "TP": "TAP Portugal",
    "LX": "Swiss", "AZ": "ITA Airways", "KL": "KLM", "D8": "Norwegian"
}

# --- MEGA BASE DE DATOS DE AEROPUERTOS ---
aeropuertos_europa = {
    "🇬🇧 Reino Unido e Irlanda": {
        "Londres": "LON", "Dublín": "DUB", "Edimburgo": "EDI", "Mánchester": "MAN", 
        "Bristol": "BRS", "Glasgow": "GLA", "Birmingham": "BHX", "Liverpool": "LPL", "Belfast": "BFS"
    },
    "🇫🇷 Francia": {
        "París": "PAR", "Niza": "NCE", "Lyon": "LYS", "Marsella": "MRS", 
        "Burdeos": "BOD", "Toulouse": "TLS", "Nantes": "NTE"
    },
    "🇮🇹 Italia": {
        "Roma": "ROM", "Milán": "MIL", "Venecia": "VCE", "Nápoles": "NAP", "Bolonia": "BLQ", 
        "Pisa": "PSA", "Florencia": "FLR", "Turín": "TRN", "Catania": "CTA", "Palermo": "PMO", 
        "Bari": "BRI", "Cagliari": "CAG", "Bérgamo": "BGY"
    },
    "🇩🇪 Alemania / 🇨🇭 Suiza": {
        "Berlín": "BER", "Múnich": "MUC", "Frankfurt": "FRA", "Hamburgo": "HAM", "Colonia": "CGN", 
        "Viena": "VIE", "Zúrich": "ZRH", "Ginebra": "GVA", "Basilea": "BSL"
    },
    "🇪🇸 España (Islas/Norte)": {
        "Mallorca": "PMI", "Ibiza": "IBZ", "Menorca": "MAH", 
        "Tenerife": "TCI", "Gran Canaria": "LPA", "Lanzarote": "ACE", 
        "Bilbao": "BIO", "Santiago": "SCQ"
    },
    "🇵🇹 Portugal": {
        "Lisboa": "LIS", "Oporto": "OPO", "Faro": "FAO", "Madeira": "FNC", "Azores": "PDL"
    },
    "🇳🇱 Benelux": {
        "Ámsterdam": "AMS", "Eindhoven": "EIN", "Bruselas": "BRU", "Charleroi": "CRL", "Luxemburgo": "LUX"
    },
    "🇪🇺 Europa Este": {
        "Praga": "PRG", "Budapest": "BUD", "Varsovia": "WAW", "Cracovia": "KRK", 
        "Bucarest": "OTP", "Sofía": "SOF"
    },
    "❄️ Nórdicos": {
        "Copenhague": "CPH", "Estocolmo": "STO", "Oslo": "OSL", "Helsinki": "HEL", "Reikiavik": "KEF"
    },
    "☀️ Mediterráneo": {
        "Atenas": "ATH", "Santorini": "JTR", "Mykonos": "JMK", "Estambul": "IST", 
        "Malta": "MLA", "Dubrovnik": "DBV", "Split": "SPU"
    }
}

# --- PROCESAMIENTO DE NOMBRES ---
catalogo_limpio = {}
ciudades_por_region = {}

for region, ciudades in aeropuertos_europa.items():
    bandera = region.split()[0]
    lista_temporal = []
    for nombre_ciudad, codigo in ciudades.items():
        nombre_bonito = f"{bandera} {nombre_ciudad}"
        catalogo_limpio[nombre_bonito] = codigo
        lista_temporal.append(nombre_bonito)
    ciudades_por_region[region] = lista_temporal

# --- FUNCIÓN DE CACHÉ ---
@st.cache_data(ttl=3600, show_spinner=False)
def buscar_vuelos_api(origen, destino_code, fecha_ida, fecha_vuelta):
    # NOTA: No pasamos las keys como argumento para que el cache funcione mejor,
    # las lee de las variables globales que ya cargamos arriba.
    try:
        # IMPORTANTE: hostname='production' para datos reales
        amadeus = Client(client_id=API_KEY, client_secret=API_SECRET, hostname='production')
        
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origen,
            destinationLocationCode=destino_code,
            departureDate=fecha_ida,
            returnDate=fecha_vuelta,
            adults=1,
            currencyCode='EUR',
            max=40 
        )
        
        vuelos_limpios = []
        for vuelo in response.data:
            itin = vuelo['itineraries']
            
            # FILTRO: Solo directos
            if len(itin[0]['segments']) > 1 or len(itin[1]['segments']) > 1:
                continue
                
            s_ida = itin[0]['segments'][0]
            s_vuelta = itin[1]['segments'][0]
            
            code_carrier = s_ida['carrierCode']
            nombre_carrier = nombres_aerolineas.get(code_carrier, code_carrier)
            
            vuelos_limpios.append({
                'precio': float(vuelo['price']['total']),
                'aerolinea': nombre_carrier,
                'salida_ida': s_ida['departure']['at'],
                'salida_vuelta': s_vuelta['departure']['at']
            })
            
        return vuelos_limpios

    except ResponseError as error:
        if error.response.statusCode == 429: return "RATE_LIMIT"
        return []
    except Exception:
        return []

# --- FUNCIÓN LINKS ---
def generar_link_skyscanner(destino, f_ida, f_vuelta):
    fi = f_ida.replace("-", "")[2:]
    fv = f_vuelta.replace("-", "")[2:]
    return f"https://www.skyscanner.es/transport/flights/mad/{destino.lower()}/{fi}/{fv}/"

# --- INTERFAZ ---
st.title("🚀 EuroTrip Pro: Buscador Inteligente")

with st.sidebar:
    st.header("⚙️ Configuración")
    
    # FECHAS
    st.subheader("📅 Fechas")
    fecha_inicio_usuario = st.date_input("¿A partir de cuándo buscar?", datetime.now())
    semanas_a_mirar = st.slider("¿Cuántos fines de semana revisar?", 1, 8, 4)
    tipo_escapada = st.radio("🗓️ Duración", ["Viernes a Domingo", "Viernes a Sábado"])
    dias_estancia = 2 if "Domingo" in tipo_escapada else 1
    
    # HORARIOS
    st.subheader("⏰ Horarios")
    h_ida = st.slider("Salida Viernes >", 0, 23, 15, format="%dh")
    dia_vuelta_txt = "Dom" if dias_estancia == 2 else "Sáb"
    h_vuelta = st.slider(f"Regreso {dia_vuelta_txt} >", 0, 23, 16, format="%dh")

    # DESTINOS
    st.subheader("📍 Destinos")
    filtro_region = st.selectbox("Filtrar por zona:", ["Todas las zonas"] + list(aeropuertos_europa.keys()))
    
    opciones_a_mostrar = []
    if filtro_region == "Todas las zonas":
        for lista in ciudades_por_region.values():
            opciones_a_mostrar.extend(lista)
        opciones_a_mostrar.sort()
    else:
        opciones_a_mostrar = ciudades_por_region[filtro_region]

    if filtro_region != "Todas las zonas":
        if st.button(f"Seleccionar todo {filtro_region}"):
            st.session_state['destinos_elegidos'] = opciones_a_mostrar
    
    destinos = st.multiselect("Elige ciudades:", options=opciones_a_mostrar, key='destinos_elegidos', default=[])
    
    presupuesto = st.number_input("Presupuesto Máx (€)", value=150, step=10)
    buscar = st.button("🔎 RASTREAR VUELOS", type="primary")

# --- LÓGICA PRINCIPAL ---
if buscar:
    if not destinos:
        st.error("¡Selecciona al menos un destino!")
    else:
        dias_a_viernes = (4 - fecha_inicio_usuario.weekday() + 7) % 7
        if dias_a_viernes == 0: dias_a_viernes = 0
        primer_viernes = fecha_inicio_usuario + timedelta(days=dias_a_viernes)
        
        fechas_a_buscar = []
        for i in range(semanas_a_mirar):
            ida = primer_viernes + timedelta(weeks=i)
            vuelta = ida + timedelta(days=dias_estancia)
            fechas_a_buscar.append((ida, vuelta))

        total_pasos = len(destinos) * len(fechas_a_buscar)
        barra = st.progress(0)
        status = st.empty()
        contador = 0
        encontrados = 0
        
        for fecha_ida, fecha_vuelta in fechas_a_buscar:
            f_ida_str = fecha_ida.strftime('%Y-%m-%d')
            f_vuelta_str = fecha_vuelta.strftime('%Y-%m-%d')
            
            with st.expander(f"🗓️ {fecha_ida.strftime('%d %b')} - {fecha_vuelta.strftime('%d %b')}", expanded=True):
                cols = st.columns(3)
                idx_col = 0
                hay_vuelos_fecha = False
                
                for nombre_limpio in destinos:
                    codigo = catalogo_limpio[nombre_limpio]
                    contador += 1
                    barra.progress(contador / total_pasos)
                    status.markdown(f"📡 Verificando **{nombre_limpio}** ({f_ida_str})...")
                    
                    datos_vuelos = buscar_vuelos_api(
                        'MAD', codigo, f_ida_str, f_vuelta_str
                    )
                    
                    if datos_vuelos == "RATE_LIMIT":
                        time.sleep(5)
                        continue
                    
                    mejores = []
                    for v in datos_vuelos:
                        t_salida = datetime.strptime(v['salida_ida'], "%Y-%m-%dT%H:%M:%S")
                        t_regreso = datetime.strptime(v['salida_vuelta'], "%Y-%m-%dT%H:%M:%S")
                        
                        if t_salida.hour >= h_ida and t_regreso.hour >= h_vuelta and v['precio'] <= presupuesto:
                            mejores.append({
                                'precio': v['precio'],
                                'aerolinea': v['aerolinea'],
                                'ida': t_salida.strftime('%H:%M'),
                                'vuelta': t_regreso.strftime('%H:%M')
                            })
                    
                    if mejores:
                        mejores.sort(key=lambda x: x['precio'])
                        top = mejores[0]
                        
                        with cols[idx_col % 3]:
                            st.success(f"{nombre_limpio}")
                            st.metric("Directo", f"{top['precio']} €")
                            st.caption(f"✈️ {top['aerolinea']} | {top['ida']} - {top['vuelta']}")
                            st.link_button("🎟️ Comprar", generar_link_skyscanner(codigo, f_ida_str, f_vuelta_str))
                        
                        idx_col += 1
                        encontrados += 1
                        hay_vuelos_fecha = True
                    
                    time.sleep(0.1) 
                
                if not hay_vuelos_fecha:
                    st.caption("Sin opciones válidas.")

        barra.empty()
        status.empty()
        if encontrados > 0:
            st.balloons()
            st.success(f"¡Hecho! {encontrados} vuelos encontrados.")
        else:
            st.warning("No hubo suerte. Prueba a cambiar fechas o presupuesto.")
