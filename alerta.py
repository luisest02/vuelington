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
MESES_VISTA = 2 # Mantenemos 2 meses para permitir la doble búsqueda sin coste extra
SEMANAS_A_MIRAR = MESES_VISTA * 4 

# 🌍 LISTA "EUROTRIP BALCANES & ESTE" (Top 21)
DESTINOS = [
    # 💎 LA NUEVA OLA (Albania, Rumanía, Croacia) - Muy baratos y de moda
    "TIA", # Tirana (Albania) - La joya de moda
    "OTP", # Bucarest (Rumanía) - Vida nocturna top
    "CLJ", # Cluj-Napoca (Rumanía) - Ciudad universitaria y de festivales
    "ZAG", # Zagreb (Croacia) - Capital preciosa y económica
    "SOF", # Sofía (Bulgaria) - De lo más barato de Europa

    # 🍻 POLONIA & HUNGRÍA (Fiesta asegurada)
    "KRK", # Cracovia (Imprescindible con amigos)
    "WAW", # Varsovia (Mezcla historia y rascacielos)
    "BUD", # Budapest (Termas y Ruin Bars)
    "PRG", # Praga (Cerveza y vistas)

    # 🏛️ CLÁSICOS & FIESTA
    "BER", # Berlín (Techno)
    "AMS", # Ámsterdam (Canales)
    "DUB", # Dublín (Pubs)
    "BRU", # Bruselas (Cerveza fuerte)
    "MLA", # Malta (Sol y fiesta mediterránea)

    # 🍕 ITALIA (Siempre renta)
    "ROM", # Roma
    "MIL", # Milán
    "VCE", # Venecia
    "NAP", # Nápoles (Caos divertido)
    "BLQ", # Bolonia (Ambiente universitario)

    # 🎩 LOS GRANDES
    "LON", # Londres
    "PAR"  # París
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

    print(f"🔎 Buscando Eurotrips (V-D y S-D) a {MESES_VISTA} meses vista...")

    # BUCLE DE FECHAS
    for i in range(SEMANAS_A_MIRAR):
        # Fechas base de esa semana
        date_viernes = primer_viernes + timedelta(weeks=i)
        date_sabado = date_viernes + timedelta(days=1)
        date_domingo = date_viernes + timedelta(days=2)
        
        str_viernes = date_viernes.strftime('%Y-%m-%d')
        str_sabado = date_sabado.strftime('%Y-%m-%d')
        str_domingo = date_domingo.strftime('%Y-%m-%d')
        
        # DEFINIMOS LAS 2 BÚSQUEDAS POR SEMANA
        opciones_busqueda = [
            # Opción 1: Viernes Tarde -> Domingo (Cualquier hora vuelta)
            {"ida": str_viernes, "vuelta": str_domingo, "tag": "V-D", "h_min": 14, "h_max": 23},
            # Opción 2: Sábado Mañana -> Domingo Tarde (Estricto)
            {"ida": str_sabado, "vuelta": str_domingo, "tag": "S-D", "h_min": 5, "h_max": 14}
        ]

        # BUCLE DE CIUDADES
        for codigo in DESTINOS:
            for opcion in opciones_busqueda:
                try:
                    res = amadeus.shopping.flight_offers_search.get(
                        originLocationCode=ORIGEN, destinationLocationCode=codigo,
                        departureDate=opcion["ida"], returnDate=opcion["vuelta"],
                        adults=1, currencyCode='EUR', max=1 
                    )
                    
                    if not res.data: continue
                    vuelo = res.data[0] 

                    # 1. Filtro Precio
                    precio = float(vuelo['price']['total'])
                    if precio > PRECIO_CHOLLO: continue

                    segs_ida = vuelo['itineraries'][0]['segments']
                    segs_vuelta = vuelo['itineraries'][1]['segments']
                    
                    # 2. Filtro Horario IDA
                    h_salida = int(segs_ida[0]['departure']['at'].split('T')[1][:2])
                    if not (opcion["h_min"] <= h_salida <= opcion["h_max"]): continue
                    
                    # 3. Filtro Horario VUELTA (Domingo)
                    h_regreso = int(segs_vuelta[0]['departure']['at'].split('T')[1][:2])
                    
                    # Si es la opción Sábado-Domingo, exigimos volver tarde (>15:00)
                    if opcion["tag"] == "S-D" and h_regreso < 15: continue
                    
                    # Preparar datos
                    h_ida_str = segs_ida[0]['departure']['at'].split('T')[1][:5]
                    h_vuelta_str = segs_vuelta[0]['departure']['at'].split('T')[1][:5]
                    aerolinea = segs_ida[0]['carrierCode']
                    
                    icono = "⚡" if opcion["tag"] == "S-D" else "📅" 
                    fecha_bonita = f"{opcion['ida'][8:]}/{opcion['ida'][5:7]}"

                    ranking_global.append({
                        'precio': precio,
                        'linea': f"{icono} {codigo} ({fecha_bonita}): **{precio}€** | {opcion['tag']} {h_ida_str}-{h_vuelta_str} ({aerolinea})"
                    })
                    
                except Exception:
                    continue

    # --- ENVIAR RESUMEN ---
    if ranking_global:
        ranking_global.sort(key=lambda x: x['precio'])
        
        msg = f"🌍 **EUROTRIP FRIENDS** (Próx {MESES_VISTA} meses)\n_Top Chollos (V-D y S-D):_\n\n"
        for item in ranking_global[:25]:
            msg += item['linea'] + "\n"
        
        enviar_telegram(msg)
        print("✅ Resumen enviado.")
    else:
        print("🤷‍♂️ Nada interesante.")

except Exception as e:
    print(f"❌ Error: {e}")
