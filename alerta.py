import os
import requests
from datetime import datetime, timedelta
import time
import re

# --- CONFIGURACIÓN ---
SEMANAS_A_MIRAR = 13
PRECIO_MAXIMO = 200
DESTINO_BOT = "/m/02j9z" # Europa

try:
    SERPAPI_KEY = os.environ["SERPAPI_KEY"]
    TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
    TG_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
except KeyError:
    print("❌ Error: Faltan secretos (Environment Variables).")
    exit()

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True})

def buscar_vuelos_google(f_ida, f_vuelta):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "departure_id": "MAD",
        "arrival_id": DESTINO_BOT, 
        "outbound_date": f_ida,
        "return_date": f_vuelta,
        "currency": "EUR",
        "hl": "es",
        "api_key": SERPAPI_KEY,
        "stops": "0",
        "price_max": PRECIO_MAXIMO,
        "outbound_times": "15,23", # Viernes tarde
        "return_times": "16,23"    # Domingo tarde
    }

    try:
        res = requests.get(url, params=params, timeout=30)
        data = res.json()
        
        if "error" in data:
            print(f"⚠️ Error API Google: {data['error']}")
            return []
            
        # MEJORA: Combinar listas como en la app manual
        raw = data.get("best_flights", []) + data.get("other_flights", []) + data.get("destinations", [])
        
        clean = []
        for v in raw:
            try:
                # 1. Parsing Precio
                p_val = 9999
                p_raw = v.get("price", v.get("flight_cost"))
                
                if isinstance(p_raw, int): p_val = p_raw
                elif isinstance(p_raw, str):
                    nums = re.findall(r'\d+', p_raw)
                    if nums: p_val = int(nums[0])
                
                if p_val > PRECIO_MAXIMO: continue

                # 2. Parsing Datos
                if "flights" in v:
                    seg = v["flights"][0]
                    dest = seg["arrival_airport"]["name"]
                else:
                    dest = v.get("name", "Destino")

                # 3. Link
                link = f"https://www.google.com/travel/flights?q=Flights%20to%20{dest}%20from%20MAD%20on%20{f_ida}%20returning%20{f_vuelta}"

                clean.append({"destino": dest, "precio": p_val, "link": link})
            except Exception:
                continue

        clean.sort(key=lambda x: x['precio'])
        return clean

    except Exception as e:
        print(f"❌ Error Excepción: {e}")
        return []

# --- EJECUCIÓN ---
print("🚀 Iniciando escaneo semanal...")
reporte = []

hoy = datetime.now()
dias_viernes = (4 - hoy.weekday() + 7) % 7
if dias_viernes == 0: dias_viernes = 7
primer_viernes = hoy + timedelta(days=dias_viernes)

for i in range(SEMANAS_A_MIRAR):
    v = primer_viernes + timedelta(weeks=i)
    d = v + timedelta(days=2)
    s_v, s_d = v.strftime('%Y-%m-%d'), d.strftime('%Y-%m-%d')
    
    print(f"🔎 Escaneando finde {s_v}...")
    vuelos = buscar_vuelos_google(s_v, s_d)
    
    if vuelos:
        top = vuelos[:3] # Top 3 más baratos por fin de semana
        txt = f"🗓️ **{v.strftime('%d/%b')}**"
        for x in top:
            txt += f"\n✈️ [{x['destino']}]({x['link']}) **{x['precio']}€**"
        reporte.append(txt)
    
    time.sleep(1) # Respetar API rate limits

if reporte:
    msg = "\n\n".join(reporte)
    enviar_telegram(f"🌍 **RESUMEN VUELOS (V-D Tarde)**\n\n{msg}")
    print("✅ Reporte enviado a Telegram.")
else:
    print("⚠️ Nada encontrado por debajo del precio máximo.")
