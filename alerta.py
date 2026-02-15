import os
import requests
from datetime import datetime, timedelta
import time

# --- CONFIGURACIÓN ---
# Consigue tu API Key en serpapi.com (Plan Free)
try:
    SERPAPI_KEY = os.environ["SERPAPI_KEY"] # ¡Crea este secreto en GitHub!
    TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
    TG_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
except KeyError:
    print("❌ Faltan secretos (SERPAPI_KEY, TELEGRAM...).")
    exit()

ORIGEN = "MAD"
DESTINO_GENERAL = "Europe" # Buscamos en todo el continente
PRECIO_MAXIMO = 180       # Sube un poco, Google suele dar precios finales
SEMANAS_A_MIRAR = 8       # Miramos 2 meses vista

# --- FILTROS INTELIGENTES DE HORARIO ---
# Formato SerpApi: "HHMM,HHMM" (Rango de horas)
HORA_IDA = "1400,2359"    # Viernes a partir de las 14:00
HORA_VUELTA = "1600,2359" # Domingo a partir de las 16:00 (para aprovechar el día)

def enviar_telegram(msg):
    if not msg: return
    if len(msg) > 4000: msg = msg[:4000] + "..."
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def buscar_google_smart(fecha_ida, fecha_vuelta):
    url = "https://serpapi.com/search"
    
    params = {
        "engine": "google_flights",
        "departure_id": ORIGEN,
        "arrival_id": DESTINO_GENERAL, # Truco: Buscamos a "Europa"
        "outbound_date": fecha_ida,
        "return_date": fecha_vuelta,
        "currency": "EUR",
        "hl": "es", # Idioma español para nombres de ciudades
        "api_key": SERPAPI_KEY,
        
        # 🔥 AQUÍ ESTÁ LA MAGIA DEL FILTRO HORARIO
        "outbound_times": HORA_IDA,   # Filtra la ida
        "return_times": HORA_VUELTA,  # Filtra la vuelta
        "stops": "0",                 # 0 = Solo directos (opcional, ahorra tiempo)
        "type": "1"                   # 1 = Round Trip
    }
    
    try:
        # Esto consume 1 crédito de búsqueda
        data = requests.get(url, params=params).json()
        
        # Google devuelve "price_graph" o "other_flights" en búsquedas generales.
        # A veces, para "Europe", devuelve una lista de destinos en 'other_flights'
        # o dentro de 'destinations' (depende de cómo responda Google ese día).
        
        resultados = []
        
        # Estrategia: Google suele devolver "other_flights" con listas de destinos
        vuelos = data.get("other_flights", [])
        
        # Si no hay vuelos directos en la lista principal, a veces da nada.
        if not vuelos:
             print(f"💨 Sin resultados para {fecha_ida}")
             return []

        for v in vuelos:
            # Estructura típica de SerpApi Google Flights
            try:
                precio = v.get("price", 9999)
                if precio > PRECIO_MAXIMO: continue
                
                # Extraer destino
                destino = v["flights"][0]["arrival_airport"]["name"]
                aerolinea = v["flights"][0]["airline"]
                
                # Horarios reales (Google ya ha filtrado, pero para mostrarlo)
                # OJO: En vista "Explore" a veces resume la info.
                h_salida = v["flights"][0]["departure_airport"]["time"]
                h_regreso = v["flights"][-1]["departure_airport"]["time"]
                
                resultados.append({
                    "destino": destino,
                    "precio": precio,
                    "aerolinea": aerolinea,
                    "h_ida": h_salida,
                    "h_vuelta": h_regreso
                })
            except:
                continue
                
        return resultados

    except Exception as e:
        print(f"Error API: {e}")
        return []

# --- MAIN ---
print(f"🚀 Iniciando barrido inteligente Google Flights ({SEMANAS_A_MIRAR} findes)...")
reporte = []

# Calculamos próximo Viernes
hoy = datetime.now()
dias_hasta_viernes = (4 - hoy.weekday() + 7) % 7
if dias_hasta_viernes == 0: dias_hasta_viernes = 7
primer_viernes = hoy + timedelta(days=dias_hasta_viernes)

for i in range(SEMANAS_A_MIRAR):
    # Fechas
    viernes = primer_viernes + timedelta(weeks=i)
    domingo = viernes + timedelta(days=2)
    
    s_viernes = viernes.strftime('%Y-%m-%d')
    s_domingo = domingo.strftime('%Y-%m-%d')
    fecha_humana = viernes.strftime('%d/%m')
    
    print(f"🔎 Mirando finde {fecha_humana}...")
    
    # 1 LLAMADA A LA API (Busca en toda Europa a la vez)
    chollos = buscar_google_smart(s_viernes, s_domingo)
    
    if chollos:
        # Ordenamos por precio
        chollos.sort(key=lambda x: x['precio'])
        
        top_3 = chollos[:3] # Nos quedamos los 3 mejores de ese finde
        
        txt_finde = f"🗓️ **{fecha_humana}**:"
        for c in top_3:
            # Link para comprar
            link = f"https://www.google.com/travel/flights?q=Flights%20to%20{c['destino']}%20on%20{s_viernes}%20through%20{s_domingo}"
            txt_finde += f"\n✈️ [{c['destino']}]({link}) **{c['precio']}€** ({c['h_ida']}-{c['h_vuelta']})"
        
        reporte.append(txt_finde)
    
    # Pausa de seguridad (aunque SerpApi aguanta bien)
    time.sleep(1)

if reporte:
    cuerpo = "\n\n".join(reporte)
    enviar_telegram(f"⚡ **GOOGLE SNIPER ALERT** ⚡\n_Filtro: V({HORA_IDA.replace(',','-')}) - D({HORA_VUELTA.replace(',','-')})_\n\n{cuerpo}")
    print("✅ Enviado.")
else:
    print("No se encontraron vuelos baratos en tus horarios.")
