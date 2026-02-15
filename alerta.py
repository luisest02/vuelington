import os
import requests
from datetime import datetime, timedelta
import time

# --- CONFIGURACIÓN ---
SEMANAS_A_MIRAR = 13     # 3 Meses exactos
PRECIO_MAXIMO = 200      # Tu límite
DESTINO_BOT = "Europe"   # Para <200€ es lo más eficiente.

try:
    SERPAPI_KEY = os.environ["SERPAPI_KEY"]
    TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
    TG_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
except KeyError:
    print("❌ Error: Faltan secretos en GitHub.")
    exit()

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    # Cortar si es muy largo
    if len(msg) > 4000: msg = msg[:4000] + "\n...(cortado)"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def buscar_vuelos_google(fecha_ida, fecha_vuelta):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "departure_id": "MAD",
        "arrival_id": DESTINO_BOT, 
        "outbound_date": fecha_ida,
        "return_date": fecha_vuelta,
        "currency": "EUR",
        "hl": "es",
        "api_key": SERPAPI_KEY,
        "stops": "0",       # Solo directos
        "outbound_times": "1400,2359", # Viernes tarde
        "return_times": "1500,2359"    # Domingo tarde
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        # Gestión de errores de API agotada
        if "error" in data:
            print(f"⚠️ Error API: {data['error']}")
            return []

        vuelos = data.get("other_flights", [])
        if not vuelos: return []

        chollos = []
        for v in vuelos:
            try:
                precio = v.get("price", 9999)
                if precio > PRECIO_MAXIMO: continue
                
                destino = v["flights"][0]["arrival_airport"]["name"]
                aerolinea = v["flights"][0]["airline"]
                
                # Formatear horas
                h_ida = v["flights"][0]["departure_airport"]["time"]
                h_vuelta = v["flights"][-1]["departure_airport"]["time"]
                
                chollos.append({
                    "destino": destino,
                    "precio": precio,
                    "info": f"{h_ida}-{h_vuelta} ({aerolinea})"
                })
            except:
                continue
        return chollos
    except Exception as e:
        print(f"Error Crítico: {e}")
        return []

# --- EJECUCIÓN ---
print(f"🚀 Iniciando barrido a {SEMANAS_A_MIRAR} semanas (Europa < {PRECIO_MAXIMO}€)...")
reporte = []

# Calcular el próximo viernes
hoy = datetime.now()
dias_viernes = (4 - hoy.weekday() + 7) % 7
if dias_viernes == 0: dias_viernes = 7
primer_viernes = hoy + timedelta(days=dias_viernes)

for i in range(SEMANAS_A_MIRAR):
    viernes = primer_viernes + timedelta(weeks=i)
    domingo = viernes + timedelta(days=2)
    
    s_viernes = viernes.strftime('%Y-%m-%d')
    s_domingo = domingo.strftime('%Y-%m-%d')
    fecha_humana = viernes.strftime('%d/%b')
    
    print(f"🔎 {fecha_humana}...")
    
    res = buscar_vuelos_google(s_viernes, s_domingo)
    
    if res:
        res.sort(key=lambda x: x['precio'])
        top = res[:3] # Top 3
        
        txt = f"🗓️ **{fecha_humana}**"
        for c in top:
            link = f"https://www.google.com/travel/flights?q=Flights%20to%20{c['destino']}%20on%20{s_viernes}%20through%20{s_domingo}"
            txt += f"\n✈️ [{c['destino']}]({link}) **{c['precio']}€** {c['info']}"
        reporte.append(txt)
        
    time.sleep(1) # Respeto a la API

if reporte:
    cuerpo = "\n\n".join(reporte)
    # Header del mensaje
    header = f"🌍 **VUELINGTON 3-MESES**\n_Filtro: <{PRECIO_MAXIMO}€ | V-D Tarde_\n\n"
    enviar_telegram(header + cuerpo)
else:
    print("Sin chollos hoy.")
