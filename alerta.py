import os
import requests
from datetime import datetime, timedelta
import time
import re

# --- CONFIGURACIÓN OPTIMIZADA ---
SEMANAS_A_MIRAR = 6  # 📉 REDUCIDO: Miramos a mes y medio vista para AHORRAR TOKENS
PRECIO_MAXIMO = 150  # Ajusta tu presupuesto máximo
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
    # 🟢 CORRECCIÓN: Enviamos como 'json' para que Telegram no falle
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
        "type": "1",               # 🔒 FUERZA IDA Y VUELTA: Siempre vuelve a MAD
        "price_max": PRECIO_MAXIMO,
        "outbound_times": "05,12", # 🌅 SÁBADO: Salidas solo de 05:00 a 12:00
        "return_times": "16,23"    # 🌇 DOMINGO: Regresos solo de 16:00 a 23:59
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

                # 3. Link Robusto
                link = f"https://www.google.com/travel/flights?q=Flights%20to%20{dest}%20from%20MAD%20on%20{f_ida}%20returning%20{f_vuelta}"

                clean.append({"destino": dest, "precio": p_val, "link": link})
            except Exception:
                continue

        # Ordenar de más barato a más caro
        clean.sort(key=lambda x: x['precio'])
        return clean

    except Exception as e:
        print(f"❌ Error Excepción: {e}")
        return []

# --- EJECUCIÓN (Lógica de Sábado a Domingo) ---
print("🚀 Iniciando escaneo de escapadas (Sab-Dom)...")
reporte = []

hoy = datetime.now()
# 📅 LÓGICA: Encontrar el próximo SÁBADO (Día 5 de la semana en Python)
dias_sabado = (5 - hoy.weekday() + 7) % 7
if dias_sabado == 0: dias_sabado = 7 # Si hoy es sábado, miramos el de la semana que viene
primer_sabado = hoy + timedelta(days=dias_sabado)

for i in range(SEMANAS_A_MIRAR):
    v = primer_sabado + timedelta(weeks=i)
    d = v + timedelta(days=1) # 📅 LÓGICA: Sumamos 1 solo día para volver el DOMINGO
    s_v, s_d = v.strftime('%Y-%m-%d'), d.strftime('%Y-%m-%d')
    
    print(f"🔎 Escaneando finde exprés {s_v}...")
    vuelos = buscar_vuelos_google(s_v, s_d)
    
    if vuelos:
        top = vuelos[:3] # Top 3 más baratos por fin de semana
        txt = f"🗓️ **{v.strftime('%d/%b')} al {d.strftime('%d/%b')}**"
        for x in top:
            txt += f"\n✈️ [{x['destino']}]({x['link']}) **{x['precio']}€**"
        reporte.append(txt)
    
    time.sleep(1) # Respetar API rate limits

if reporte:
    msg = "\n\n".join(reporte)
    enviar_telegram(f"🌍 **CHOLLOS 1 DÍA (Sab Mañana - Dom Tarde)**\n\n{msg}")
    print("✅ Reporte enviado a Telegram.")
else:
    print("⚠️ Nada encontrado por debajo del precio máximo.")
