import os
import requests
from datetime import datetime, timedelta
import time

# --- CONFIGURACIÓN ---
# Busca vuelos a 2 meses vista (8 fines de semana)
SEMANAS_A_MIRAR = 8 
PRECIO_MAXIMO = 200 # Avisar si baja de esto

try:
    # Carga los secretos desde GitHub Actions
    SERPAPI_KEY = os.environ["SERPAPI_KEY"]
    TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
    TG_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
except KeyError:
    print("❌ Error: Faltan secretos en GitHub.")
    exit()

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def buscar_vuelos_google(fecha_ida, fecha_vuelta):
    # ESTRATEGIA: Buscamos a "Europe" en general para gastar solo 1 petición
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "departure_id": "MAD",
        "arrival_id": "Europe", # Truco para ahorrar API
        "outbound_date": fecha_ida,
        "return_date": fecha_vuelta,
        "currency": "EUR",
        "hl": "es",
        "api_key": SERPAPI_KEY,
        "stops": "0",       # Solo vuelos directos
        
        # --- FILTROS DE HORARIO (Viernes Tarde - Domingo Tarde) ---
        # Salida: 14:00 (2pm) a 23:59
        "outbound_times": "1400,2359", 
        # Vuelta: 15:00 (3pm) a 23:59
        "return_times": "1500,2359"    
    }

    try:
        data = requests.get(url, params=params).json()
        
        # Google devuelve los resultados en 'other_flights' cuando la búsqueda es genérica
        vuelos = data.get("other_flights", [])
        if not vuelos: return []

        chollos = []
        for v in vuelos:
            try:
                precio = v.get("price", 9999)
                if precio > PRECIO_MAXIMO: continue
                
                destino = v["flights"][0]["arrival_airport"]["name"]
                aerolinea = v["flights"][0]["airline"]
                hora_ida = v["flights"][0]["departure_airport"]["time"]
                hora_vuelta = v["flights"][-1]["departure_airport"]["time"]
                
                chollos.append({
                    "destino": destino,
                    "precio": precio,
                    "info": f"{hora_ida}-{hora_vuelta} ({aerolinea})"
                })
            except:
                continue
        return chollos
    except Exception as e:
        print(f"Error: {e}")
        return []

# --- EJECUCIÓN ---
print("🚀 Iniciando búsqueda inteligente...")
reporte = []

# Calcular el próximo viernes
hoy = datetime.now()
dias_hasta_viernes = (4 - hoy.weekday() + 7) % 7
if dias_hasta_viernes == 0: dias_hasta_viernes = 7
primer_viernes = hoy + timedelta(days=dias_hasta_viernes)

# Revisamos los próximos 8 fines de semana
for i in range(SEMANAS_A_MIRAR):
    viernes = primer_viernes + timedelta(weeks=i)
    domingo = viernes + timedelta(days=2)
    
    s_viernes = viernes.strftime('%Y-%m-%d')
    s_domingo = domingo.strftime('%Y-%m-%d')
    fecha_humana = viernes.strftime('%d/%b')
    
    print(f"🔎 Mirando finde {fecha_humana}...")
    
    # 1 PETICIÓN API por fin de semana
    resultados = buscar_vuelos_google(s_viernes, s_domingo)
    
    if resultados:
        resultados.sort(key=lambda x: x['precio'])
        top = resultados[:3] # Top 3 más baratos
        
        txt = f"🗓️ **{fecha_humana}**"
        for c in top:
            link = f"https://www.google.com/travel/flights?q=Flights%20to%20{c['destino']}%20from%20MAD%20on%20{s_viernes}%20through%20{s_domingo}"
            txt += f"\n✈️ [{c['destino']}]({link}) **{c['precio']}€** {c['info']}"
        reporte.append(txt)
        
    time.sleep(1) # Pausa para no saturar

if reporte:
    cuerpo = "\n\n".join(reporte)
    enviar_telegram(f"⚡ **ALERTAS FINDE (V tarde - D tarde)** ⚡\n\n{cuerpo}")
else:
    print("Nada interesante encontrado hoy.")
