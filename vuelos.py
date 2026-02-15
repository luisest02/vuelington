import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="VUELINTON PRO", page_icon="✈️", layout="wide")

# ==========================================
# 🔐 GESTIÓN DE SECRETOS (DEBUG)
# ==========================================
# Verificamos que la clave exista antes de arrancar nada
if "SERPAPI_KEY" not in st.secrets:
    st.error("🚨 ERROR CRÍTICO: No se encuentra 'SERPAPI_KEY' en los secretos.")
    st.info("Ve a 'Settings' > 'Secrets' en Streamlit Cloud y añade tu clave.")
    st.stop()

API_KEY = st.secrets["SERPAPI_KEY"]

# Login simple (Opcional, si tienes contraseña puesta)
if "PASSWORD_APP" in st.secrets:
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        pwd = st.text_input("🔑 Contraseña", type="password")
        if pwd == st.secrets["PASSWORD_APP"]:
            st.session_state.auth = True
            st.rerun()
        st.stop()

# ==========================================
# ⚙️ BARRA LATERAL (CONFIGURACIÓN)
# ==========================================
with st.sidebar:
    st.title("🎛️ Filtros Avanzados")
    
    st.markdown("### 🕒 Horarios Finde")
    usar_filtro_horas = st.checkbox("Activar Filtro 'Finde Estricto'", value=True)
    
    if usar_filtro_horas:
        h_ida = st.slider("Salida Viernes (desde)", 0, 23, 14, format="%dh")
        h_vuelta = st.slider("Vuelta Domingo (desde)", 0, 23, 15, format="%dh")
        
        # Formato para SerpApi: "HHmm,2359" (ej: "1400,2359")
        # Aseguramos que tenga 4 dígitos rellenando con ceros
        str_ida = f"{h_ida:02d}00,2359"
        str_vuelta = f"{h_vuelta:02d}00,2359"
    else:
        str_ida = None
        str_vuelta = None
        st.caption("Buscando a cualquier hora")

    st.divider()
    
    # KPIs visuales
    st.markdown("### 📊 Estado Cuenta")
    if st.button("Chequear saldo API"):
        try:
            # Petición ligera para ver estado de cuenta
            info = requests.get(f"https://serpapi.com/account?api_key={API_KEY}").json()
            if "error" in info:
                st.error(f"Error clave: {info['error']}")
            else:
                total = info.get("total_searches_left", 0)
                st.metric("Búsquedas Restantes", total)
        except Exception as e:
            st.error(f"No conecta: {e}")

# ==========================================
# 🚀 FUNCIÓN DE BÚSQUEDA (SIN SILENCIADOR)
# ==========================================
def buscar_google_manual(origen, region_code, f_ida, f_vuelta, max_price, times_out, times_in):
    url = "https://serpapi.com/search"
    
    params = {
        "engine": "google_flights",
        "departure_id": origen,
        "outbound_date": f_ida,
        "return_date": f_vuelta,
        "currency": "EUR",
        "hl": "es",
        "api_key": API_KEY,
        "stops": "0", # Solo directos
        "type": "1"   # Ida y vuelta
    }

    # Lógica de destino: Si es "Mundo", no enviamos arrival_id
    if region_code != "Everywhere":
        params["arrival_id"] = region_code

    # Filtros de precio
    if max_price:
        params["price_max"] = max_price

    # Filtros de hora (Si están activados)
    if times_out and times_in:
        params["outbound_times"] = times_out
        params["return_times"] = times_in

    try:
        # Hacemos la petición
        response = requests.get(url, params=params)
        
        # 1. Si la API da error (401, 403, 429...) mostramos el mensaje real
        if response.status_code != 200:
            st.error(f"❌ Error API ({response.status_code}): {response.text}")
            return []

        data = response.json()

        # 2. Si Google responde pero dice error interno
        if "error" in data:
            st.error(f"❌ Google Error: {data['error']}")
            return []

        # 3. Extraer vuelos (Google a veces usa 'other_flights' o 'destinations')
        # Intentamos buscar en varios sitios del JSON
        lista_vuelos = data.get("other_flights", [])
        if not lista_vuelos:
            # Intento secundario: a veces viene en 'destinations' para mapas
            lista_vuelos = data.get("destinations", [])
            
        return lista_vuelos

    except Exception as e:
        st.error(f"🔥 Error de Conexión Python: {e}")
        return []

# ==========================================
# 🖥️ INTERFAZ PRINCIPAL
# ==========================================
st.title("✈️ VUELINGTON EXPLORER")
st.markdown("Buscador manual en tiempo real.")

col1, col2, col3 = st.columns(3)

with col1:
    f_ida = st.date_input("Ida", datetime.now() + timedelta(days=1))
with col2:
    f_vuelta = st.date_input("Vuelta", datetime.now() + timedelta(days=3))
with col3:
    region = st.selectbox("Destino", ["Europa", "Mundo Entero"])
    # Código interno para la API
    code_map = {"Europa": "Europe", "Mundo Entero": "Everywhere"}
    region_code = code_map[region]

presupuesto = st.slider("Presupuesto Máximo (€)", 50, 500, 150)

if st.button("🔎 BUSCAR VUELOS AHORA", type="primary"):
    with st.spinner(f"Conectando con Google Flights ({region})..."):
        
        resultados_raw = buscar_google_manual(
            "MAD", 
            region_code, 
            f_ida.strftime('%Y-%m-%d'), 
            f_vuelta.strftime('%Y-%m-%d'), 
            presupuesto,
            str_ida,    # Pasa el filtro de hora ida
            str_vuelta  # Pasa el filtro de hora vuelta
        )
        
        if not resultados_raw:
            st.warning("⚠️ Google no ha devuelto resultados. Prueba a subir el presupuesto o quitar el filtro de horas.")
        else:
            # Procesar datos para la tabla
            tabla = []
            for v in resultados_raw:
                try:
                    # La estructura del JSON puede variar ligeramente
                    if "flights" in v: # Estructura standard
                        seg_ida = v["flights"][0]
                        price = v.get("price", 0)
                        
                        item = {
                            "Destino": seg_ida["arrival_airport"]["name"],
                            "Precio": f"{price}€",
                            "Aerolínea": seg_ida["airline"],
                            "Salida": seg_ida["departure_airport"]["time"],
                            # Google a veces no da el link directo en la API, construimos uno
                            "Link": f"https://www.google.com/travel/flights?q=Flights%20to%20{seg_ida['arrival_airport']['id']}"
                        }
                        tabla.append(item)
                    elif "name" in v and "flight_cost" in v: # Estructura 'explore'
                         item = {
                            "Destino": v["name"],
                            "Precio": f"{v['flight_cost']}€",
                            "Aerolínea": "Varías",
                            "Salida": "N/A",
                            "Link": "https://www.google.com/travel/flights"
                        }
                         tabla.append(item)

                except Exception as e:
                    continue # Saltar item defectuoso

            if tabla:
                df = pd.DataFrame(tabla)
                # Mostramos tabla interactiva
                st.success(f"✅ Encontrados {len(tabla)} destinos")
                st.dataframe(
                    df, 
                    column_config={"Link": st.column_config.LinkColumn("Comprar")},
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Se recibieron datos pero no pude procesar el formato. Revisa los logs.")import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="VUELINTON PRO", page_icon="✈️", layout="wide")

# ==========================================
# 🔐 GESTIÓN DE SECRETOS (DEBUG)
# ==========================================
# Verificamos que la clave exista antes de arrancar nada
if "SERPAPI_KEY" not in st.secrets:
    st.error("🚨 ERROR CRÍTICO: No se encuentra 'SERPAPI_KEY' en los secretos.")
    st.info("Ve a 'Settings' > 'Secrets' en Streamlit Cloud y añade tu clave.")
    st.stop()

API_KEY = st.secrets["SERPAPI_KEY"]

# Login simple (Opcional, si tienes contraseña puesta)
if "PASSWORD_APP" in st.secrets:
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        pwd = st.text_input("🔑 Contraseña", type="password")
        if pwd == st.secrets["PASSWORD_APP"]:
            st.session_state.auth = True
            st.rerun()
        st.stop()

# ==========================================
# ⚙️ BARRA LATERAL (CONFIGURACIÓN)
# ==========================================
with st.sidebar:
    st.title("🎛️ Filtros Avanzados")
    
    st.markdown("### 🕒 Horarios Finde")
    usar_filtro_horas = st.checkbox("Activar Filtro 'Finde Estricto'", value=True)
    
    if usar_filtro_horas:
        h_ida = st.slider("Salida Viernes (desde)", 0, 23, 14, format="%dh")
        h_vuelta = st.slider("Vuelta Domingo (desde)", 0, 23, 15, format="%dh")
        
        # Formato para SerpApi: "HHmm,2359" (ej: "1400,2359")
        # Aseguramos que tenga 4 dígitos rellenando con ceros
        str_ida = f"{h_ida:02d}00,2359"
        str_vuelta = f"{h_vuelta:02d}00,2359"
    else:
        str_ida = None
        str_vuelta = None
        st.caption("Buscando a cualquier hora")

    st.divider()
    
    # KPIs visuales
    st.markdown("### 📊 Estado Cuenta")
    if st.button("Chequear saldo API"):
        try:
            # Petición ligera para ver estado de cuenta
            info = requests.get(f"https://serpapi.com/account?api_key={API_KEY}").json()
            if "error" in info:
                st.error(f"Error clave: {info['error']}")
            else:
                total = info.get("total_searches_left", 0)
                st.metric("Búsquedas Restantes", total)
        except Exception as e:
            st.error(f"No conecta: {e}")

# ==========================================
# 🚀 FUNCIÓN DE BÚSQUEDA (SIN SILENCIADOR)
# ==========================================
def buscar_google_manual(origen, region_code, f_ida, f_vuelta, max_price, times_out, times_in):
    url = "https://serpapi.com/search"
    
    params = {
        "engine": "google_flights",
        "departure_id": origen,
        "outbound_date": f_ida,
        "return_date": f_vuelta,
        "currency": "EUR",
        "hl": "es",
        "api_key": API_KEY,
        "stops": "0", # Solo directos
        "type": "1"   # Ida y vuelta
    }

    # Lógica de destino: Si es "Mundo", no enviamos arrival_id
    if region_code != "Everywhere":
        params["arrival_id"] = region_code

    # Filtros de precio
    if max_price:
        params["price_max"] = max_price

    # Filtros de hora (Si están activados)
    if times_out and times_in:
        params["outbound_times"] = times_out
        params["return_times"] = times_in

    try:
        # Hacemos la petición
        response = requests.get(url, params=params)
        
        # 1. Si la API da error (401, 403, 429...) mostramos el mensaje real
        if response.status_code != 200:
            st.error(f"❌ Error API ({response.status_code}): {response.text}")
            return []

        data = response.json()

        # 2. Si Google responde pero dice error interno
        if "error" in data:
            st.error(f"❌ Google Error: {data['error']}")
            return []

        # 3. Extraer vuelos (Google a veces usa 'other_flights' o 'destinations')
        # Intentamos buscar en varios sitios del JSON
        lista_vuelos = data.get("other_flights", [])
        if not lista_vuelos:
            # Intento secundario: a veces viene en 'destinations' para mapas
            lista_vuelos = data.get("destinations", [])
            
        return lista_vuelos

    except Exception as e:
        st.error(f"🔥 Error de Conexión Python: {e}")
        return []

# ==========================================
# 🖥️ INTERFAZ PRINCIPAL
# ==========================================
st.title("✈️ VUELINGTON EXPLORER")
st.markdown("Buscador manual en tiempo real.")

col1, col2, col3 = st.columns(3)

with col1:
    f_ida = st.date_input("Ida", datetime.now() + timedelta(days=1))
with col2:
    f_vuelta = st.date_input("Vuelta", datetime.now() + timedelta(days=3))
with col3:
    region = st.selectbox("Destino", ["Europa", "Mundo Entero"])
    # Código interno para la API
    code_map = {"Europa": "Europe", "Mundo Entero": "Everywhere"}
    region_code = code_map[region]

presupuesto = st.slider("Presupuesto Máximo (€)", 50, 500, 150)

if st.button("🔎 BUSCAR VUELOS AHORA", type="primary"):
    with st.spinner(f"Conectando con Google Flights ({region})..."):
        
        resultados_raw = buscar_google_manual(
            "MAD", 
            region_code, 
            f_ida.strftime('%Y-%m-%d'), 
            f_vuelta.strftime('%Y-%m-%d'), 
            presupuesto,
            str_ida,    # Pasa el filtro de hora ida
            str_vuelta  # Pasa el filtro de hora vuelta
        )
        
        if not resultados_raw:
            st.warning("⚠️ Google no ha devuelto resultados. Prueba a subir el presupuesto o quitar el filtro de horas.")
        else:
            # Procesar datos para la tabla
            tabla = []
            for v in resultados_raw:
                try:
                    # La estructura del JSON puede variar ligeramente
                    if "flights" in v: # Estructura standard
                        seg_ida = v["flights"][0]
                        price = v.get("price", 0)
                        
                        item = {
                            "Destino": seg_ida["arrival_airport"]["name"],
                            "Precio": f"{price}€",
                            "Aerolínea": seg_ida["airline"],
                            "Salida": seg_ida["departure_airport"]["time"],
                            # Google a veces no da el link directo en la API, construimos uno
                            "Link": f"https://www.google.com/travel/flights?q=Flights%20to%20{seg_ida['arrival_airport']['id']}"
                        }
                        tabla.append(item)
                    elif "name" in v and "flight_cost" in v: # Estructura 'explore'
                         item = {
                            "Destino": v["name"],
                            "Precio": f"{v['flight_cost']}€",
                            "Aerolínea": "Varías",
                            "Salida": "N/A",
                            "Link": "https://www.google.com/travel/flights"
                        }
                         tabla.append(item)

                except Exception as e:
                    continue # Saltar item defectuoso

            if tabla:
                df = pd.DataFrame(tabla)
                # Mostramos tabla interactiva
                st.success(f"✅ Encontrados {len(tabla)} destinos")
                st.dataframe(
                    df, 
                    column_config={"Link": st.column_config.LinkColumn("Comprar")},
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Se recibieron datos pero no pude procesar el formato. Revisa los logs.")
