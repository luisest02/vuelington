import os
import requests
from amadeus import Client, ResponseError
from datetime import datetime, timedelta
import time

# --- CARGA DE SECRETOS ---
try:
    API_KEY = os.environ["AMADEUS_API_KEY"]
    API_SECRET = os.environ["AMADEUS_API_SECRET"]
    TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
    TG_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
except KeyError:
    print("❌ Error: Faltan secretos en GitHub.")
    exit()

# --- CONFIGURACIÓN ---
ORIGEN = "MAD"
PRECIO_CHOLLO = 160 
MESES_VISTA = 3
SEMANAS_A_MIRAR = MESES_VISTA * 4 

# 🌍 LISTA DEFINITIVA "EUROTRIP FRIENDS" (Top 20)
# Optimizada matemáticamente para no pasar de 2.000 llamadas al mes.
DESTINOS = [
    # 🍻 FIESTA, AMBIENTE JOVEN & CLÁSICOS
    "AMS", # Ámsterdam (Canales y vida nocturna)
    "BER", # Berlín (La capital del Techno y la historia)
    "PRG", # Praga (Cerveza más barata que el agua)
    "BUD", # Budapest (Los Ruin Bars son obligatorios)
    "DUB", # Dublín (Ruta de pubs y Guinness)
    "BRU", # Bruselas (Gofres, patatas y cervezas fuertes)
    
    # 💎 JOYAS BARATAS (Lo mejor del Este/Sur)
    "KRK", # Cracovia (Mucha fiesta, vodka y muy barato)
    "WAW", # Varsovia (Rascacielos y casco antiguo, mezcla top)
    "SOF", # Sofía (Destino muy económico y sorprendente)
    "OTP", # Bucarest (La "París del este", vida nocturna intensa)
    "MLA", # Malta (El destino de sol y fiesta por excelencia)
    
    # 🍕 ITALIA "VIBES"
    "ROM", # Roma (Historia y pasta)
    "MIL", # Milán (Vuelos casi regalados siempre)
    "VCE", # Venecia (Única en el mundo, para ir antes de que se hunda)
    "NAP", # Nápoles (Caos, pizza real y Maradona. Brutal con amigos)
    "BLQ", # Bolonia (Ciudad universitaria, ambiente joven y comida)

    # 🎩 LOS IMPRESCINDIBLES
    "LON", # Londres (Siempre hay algo que hacer)
    "PAR", # París (Nunca falla)

    # 🇵🇹 VECINOS TOP
    "LIS", # Lisboa (Miradores, tranvías y fiesta en Barrio Alto)
    "OPO"  # Oporto (Vino, vistas al río y francesinhas)
]

def enviar_telegram(msg):
    if len(msg) > 4000:
        msg = msg[:4000] + "\n...(cortado por longitud)"
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

# --- LÓGICA PRINCIPAL ---
try:
    if "PENDIENTE" in API_KEY:
        print("⏳ Claves PENDIENTE.")
        exit()

    # CAMBIA 'test' POR 'production' CUANDO TENGAS LAS CLAVES REALES
    amadeus = Client(client_id=API_KEY, client_secret=API_SECRET, hostname='test')
    
    ranking_global = []

    # Calculamos el PRIMER viernes
    hoy = datetime.now()
    dias_viernes = (4 - hoy.weekday() + 7) % 7
    if dias_viernes == 0: dias_viernes = 7
    primer_viernes = hoy + timedelta(days=dias_viernes)

    print(f"🔎 Buscando Eurotrips a 3 meses vista (Top 20 destinos)...")

    # BUCLE DE FECHAS
    for i in range(SEMANAS_A_MIRAR):
        viernes = (primer_viernes + timedelta(weeks=i)).strftime('%Y-%m-%d')
        domingo = (primer_viernes + timedelta(weeks=i) + timedelta(days=2)).strftime('%Y-%m-%d')
        
        # BUCLE DE CIUDADES
        for codigo in DESTINOS:
            try:
                res = amadeus.shopping.flight_offers_search.get(
                    originLocationCode=ORIGEN, destinationLocationCode=codigo,
                    departureDate=viernes, returnDate=domingo,
                    adults=1, currencyCode='EUR', max=2 # Mínimo necesario
                )
                
                if not res.data: continue

                for vuelo in res.data:
                    # 1. Precio
                    precio = float(vuelo['price']['total'])
                    if precio > PRECIO_CHOLLO: continue

                    # 2. Horarios (Ida Viernes > 14:00)
                    segs_ida = vuelo['itineraries'][0]['segments']
                    segs_vuelta = vuelo['itineraries'][1]['segments']
                    
                    h_salida = int(segs_ida[0]['departure']['at'].split('T')[1][:2])
                    if h_salida < 14: continue 
                    
                    h_ida_str = segs_ida[0]['departure']['at'].split('T')[1][:5]
                    h_vuelta_str = segs_vuelta[0]['departure']['at'].split('T')[1][:5]
                    aerolinea = segs_ida[0]['carrierCode']
                    
                    # Fecha bonita (ej: 10/Feb)
                    fecha_bonita = f"{viernes[8:]}/{viernes[5:7]}"

                    ranking_global.append({
                        'precio': precio,
                        'linea': f"✈️ {codigo} ({fecha_bonita}): **{precio}€** | V{h_ida_str}-D{h_vuelta_str} ({aerolinea})"
                    })
                    
            except Exception:
                continue

    # --- ENVIAR RESUMEN ---
    if ranking_global:
        # Ordenamos por PRECIO
        ranking_global.sort(key=lambda x: x['precio'])
        
        msg = f"🌍 **EUROTRIP FRIENDS** (Próx 3 meses)\n_Top Chollos encontrados:_\n\n"
        
        # Mostramos solo el TOP 25
        for item in ranking_global[:25]:
            msg += item['linea'] + "\n"
            
        enviar_telegram(msg)
        print("✅ Enviado resumen a Telegram.")
    else:
        print("🤷‍♂️ No se encontró nada interesante.")

except Exception as e:
    print(f"❌ Error: {e}")
