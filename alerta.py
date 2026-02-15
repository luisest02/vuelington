import os
import requests
from datetime import datetime, timedelta
import time

# --- CONFIGURACIÓN ---
try:
    # ⚠️ RECUERDA: Tienes que crear el secreto SERPAPI_KEY en GitHub
    SERPAPI_KEY = os.environ["SERPAPI_KEY"]
    TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
    TG_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
except KeyError:
    print("❌ Faltan secretos en GitHub.")
    exit()

ORIGEN = "MAD"
DESTINO_GENERAL = "Europe" 
PRECIO_MAXIMO = 180       
SEMANAS_A_MIRAR = 8       # Miramos 2 meses vista (8 peticiones en total)

# --- FILTROS DE HORARIO (Formato SerpApi: HHMM..HHMM) ---
# Ida: Viernes desde las 14:00 hasta final del día
HORA_IDA = "1400..2359"    
# Vuelta: Domingo desde las 16:00 hasta final del día
HORA_VUELTA = "1600..2359" 

def enviar_telegram(msg):
    if not msg: return
    # Telegram tiene límite de 4096 caracteres
    if len(msg) > 4000: msg = msg[:4000] + "\n...(cortado)"
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def buscar_google_smart(fecha_ida, fecha_vuelta):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "departure_id": ORIGEN,
        "arrival_id": DESTINO_GENERAL,
        "outbound_date": fecha_ida,
        "return_date": fecha_vuelta,
        "currency": "EUR",
        "hl": "es",
        "api_key": SERPAPI_KEY,
        "outbound_times": HORA_IDA,   
        "return_times": HORA_VUELTA,  
        "stops": "0",                 # Solo directos
        "type": "1"                   # Ida y vuelta
    }
    
    try:
        # ⚠️ ESTO GASTA 1 CRÉDITO DE TU PLAN GRATUITO
        response = requests.get(url, params=params)
        data = response.json()
        
        # En búsquedas generales ("Europe"), los resultados suelen venir en "other_flights"
        vuelos = data.get("other_flights", [])
        
        resultados = []
        for v in vuelos:
            try:
                precio = v.get("price", 9999)
                if precio > PRECIO_MAXIMO: continue
                
                destino = v["flights"][0]["arrival_airport"]["name"]
                
                # Horarios para mostrar
                h_salida = v["flights"][0]["departure_airport"]["time"]
                h_regreso = v["flights"][-1]["departure_airport"]["time"]
                
                resultados.append({
                    "destino": destino,
                    "precio": precio,
                    "horas": f"{h_salida}-{h_regreso}"
                })
            except:
                continue
        return resultados

    except Exception as e:
        print(f"Error API: {e}")
        return []

# --- EJECUCIÓN ---
print(f"🚀 Buscando vuelos de Viernes tarde a Domingo tarde...")
reporte = []

hoy = datetime.now()
# Calcular próximo viernes
dias_viernes = (4 - hoy.weekday() + 7) % 7
if dias_viernes == 0: dias_viernes = 7
primer_viernes = hoy + timedelta(days=dias_viernes)

for i in range(SEMANAS_A_MIRAR):
    viernes = primer_viernes + timedelta(weeks=i)
    domingo = viernes + timedelta(days=2)
    
    s_viernes = viernes.strftime('%Y-%m-%d')
    s_domingo = domingo.strftime('%Y-%m-%d')
    fecha_humana = viernes.strftime('%d/%b')
    
    print(f"🔎 {fecha_humana} ({s_viernes})...")
    
    # Llamada a la API
    chollos = buscar_google_smart(s_viernes, s_domingo)
    
    if chollos:
        chollos.sort(key=lambda x: x['precio'])
        top = chollos[:3] # Top 3 destinos más baratos
        
        txt = f"🗓️ **{fecha_humana}**"
        for c in top:
            # Enlace directo a Google Flights para comprar
            link = f"https://www.google.com/travel/flights?q=Flights%20to%20{c['destino']}%20on%20{s_viernes}%20through%20{s_domingo}"
            txt += f"\n✈️ [{c['destino']}]({link}) **{c['precio']}€** ({c['horas']})"
        reporte.append(txt)
    
    # Pausa de cortesía
    time.sleep(1)

if reporte:
    cuerpo = "\n\n".join(reporte)
    enviar_telegram(f"⚡ **GOOGLE SNIPER** ⚡\n_Filtro: V({HORA_IDA}) - D({HORA_VUELTA})_\n\n{cuerpo}")
    print("✅ Enviado.")
else:
    print("Nada encontrado.")
