import os
import requests
from datetime import datetime, timedelta
import time

# --- CONFIGURACIÓN ---
SEMANAS_A_MIRAR = 13
PRECIO_MAXIMO = 200

# CORRECCIÓN AQUÍ: Usamos el ID de Europa
DESTINO_BOT = "/m/02j9z" 

try:
    SERPAPI_KEY = os.environ["SERPAPI_KEY"]
    TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
    TG_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
except KeyError:
    print("❌ Error: Faltan secretos.")
    exit()

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def buscar_vuelos_google(f_ida, f_vuelta):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "departure_id": "MAD",
        "arrival_id": DESTINO_BOT, # Usamos el código /m/02j9z
        "outbound_date": f_ida,
        "return_date": f_vuelta,
        "currency": "EUR",
        "hl": "es",
        "api_key": SERPAPI_KEY,
        "stops": "0",
        "price_max": PRECIO_MAXIMO,
        "outbound_times": "1500,2359", # Viernes tarde
        "return_times": "1600,2359"    # Domingo tarde
    }

    try:
        res = requests.get(url, params=params)
        data = res.json()
        
        if "error" in data:
            print(f"Error Google: {data['error']}")
            return []
            
        return data.get("other_flights", [])

    except: return []

# --- EJECUCIÓN ---
print("🚀 Iniciando escaneo...")
reporte = []

hoy = datetime.now()
dias_viernes = (4 - hoy.weekday() + 7) % 7
if dias_viernes == 0: dias_viernes = 7
primer_viernes = hoy + timedelta(days=dias_viernes)

for i in range(SEMANAS_A_MIRAR):
    v = primer_viernes + timedelta(weeks=i)
    d = v + timedelta(days=2)
    s_v, s_d = v.strftime('%Y-%m-%d'), d.strftime('%Y-%m-%d')
    
    print(f"🔎 {s_v}...")
    vuelos = buscar_vuelos_google(s_v, s_d)
    
    if vuelos:
        # Ordenar y coger Top 3
        vuelos.sort(key=lambda x: x.get('price', 9999))
        top = vuelos[:3]
        
        txt = f"🗓️ **{v.strftime('%d/%b')}**"
        for x in top:
            try:
                dest = x["flights"][0]["arrival_airport"]["name"]
                precio = x["price"]
                # Link directo
                link = f"https://www.google.com/travel/flights?tfs={x['flights'][0]['arrival_airport']['id']}"
                txt += f"\n✈️ [{dest}]({link}) **{precio}€**"
            except: pass
        reporte.append(txt)
    
    time.sleep(1)

if reporte:
    msg = "\n\n".join(reporte)
    enviar_telegram(f"🌍 **RESUMEN VUELOS (V-D Tarde)**\n\n{msg}")
    print("Enviado.")
else:
    print("Nada encontrado.")
