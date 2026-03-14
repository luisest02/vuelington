import os
import requests
from datetime import datetime, timedelta
import time
import re

# --- CONFIGURACIÓN ---
SEMANAS_A_MIRAR = 12  # 🔥 Aprovechamos tus 200 tokens (busca a 3 meses vista)
PRECIO_MAXIMO = 150   # Presupuesto máximo
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
    payload = {"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True}
    requests.post(url, json=payload, timeout=10)

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
        "type": "1",               # 🔒 FUERZA IDA Y VUELTA (Siempre vuelve a MADRID)
        "price_max": PRECIO_MAXIMO,
        "outbound_times": "05,12", # 🌅 SÁBADO: Salidas de 05:00 a 12:00
        "return_times": "16,23"    # 🌇 DOMINGO: Regresos de 16:00 a 23:59
    }

    try:
        res = requests.get(url, params=params, timeout=30)
        data = res.json()
        
        if "error" in data:
            print(f"⚠️ Error API Google: {data['error']}")
            return []
            
        raw = data.get("best_flights", []) + data.get("other_flights", []) + data.get("destinations", [])
        
        clean = []
        for v in raw:
            try:
                p_val = 9999
                p_raw = v.get("price", v.get("flight_cost"))
                if isinstance(p_raw, int): p_val = p_raw
                elif isinstance(p_raw, str):
                    nums = re.findall(r'\d+', p_raw)
                    if nums: p_val = int(nums[0])
                
                if p_val > PRECIO_MAXIMO: continue

                if "flights" in v:
                    seg = v["flights"][0]
                    dest = seg["arrival_airport"]["name"]
                else:
                    dest = v.get("name", "Destino")

                link = f"https://www.google.com/travel/flights?q=Flights%20to%20{dest}%20from%20MAD%20on%20{f_ida}%20returning%20{f_vuelta}"
                clean.append({"destino": dest, "precio": p_val, "link": link})
            except Exception:
                continue

        clean.sort(key=lambda x: x['precio'])
        return clean
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

# --- EJECUCIÓN (Lógica Sábado a Domingo) ---
print("🚀 Iniciando escaneo de escapadas (Sab-Dom)...")
reporte = []

hoy = datetime.now()
dias_sabado = (5 - hoy.weekday() + 7) % 7
if dias_sabado == 0: dias_sabado = 7
primer_sabado = hoy + timedelta(days=dias_sabado)

for i in range(SEMANAS_A_MIRAR):
    v = primer_sabado + timedelta(weeks=i)
    d = v + timedelta(days=1) # 📅 Suma solo 1 día para volver el DOMINGO
    s_v, s_d = v.strftime('%Y-%m-%d'), d.strftime('%Y-%m-%d')
    
    print(f"🔎 Escaneando finde exprés {s_v}...")
    vuelos = buscar_vuelos_google(s_v, s_d)
    
    if vuelos:
        top = vuelos[:3] 
        txt = f"🗓️ **{v.strftime('%d/%b')} al {d.strftime('%d/%b')}**"
        for x in top:
            txt += f"\n✈️ [{x['destino']}]({x['link']}) **{x['precio']}€**"
        reporte.append(txt)
    
    time.sleep(1)

if reporte:
    msg = "\n\n".join(reporte)
    enviar_telegram(f"🌍 **CHOLLOS 1 DÍA (Sab Mañana - Dom Tarde)**\n\n{msg}")
    print("✅ Reporte enviado.")
else:
    print("⚠️ Nada encontrado.")
