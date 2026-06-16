import asyncio
import os
import json

PORT = int(os.environ.get("PORT", 9933))
HOST = "0.0.0.0"

# --- BASE DE DATOS SIMULADA EN MEMORIA (Consumo mínimo de RAM) ---
DATA_BASE = {
    "user_profile": {
        "userId": 10001,
        "username": "PyMonster",
        "coins": 50000,
        "diamonds": 150,
        "level": 1
    },
    "islands": [
        {
            "island_id": 1, # Isla de Planta
            "unlocked": True,
            "monsters": [
                {"monster_id": 1, "name": "Noggin", "x": 10, "y": 12, "level": 1},
                {"monster_id": 2, "name": "Mammott", "x": 14, "y": 12, "level": 1}
            ]
        }
    ]
}

# --- EMULADOR DE PROTOCOLO SMARTFOX (SFS2X) ---
def parse_sfs_packet(payload):
    """Analiza los bytes entrantes del cliente de MSM original"""
    try:
        decoded = payload.decode('utf-8', errors='ignore')
        if "handshake" in decoded: return "handshake"
        if "login" in decoded: return "login"
        if "get_island" in decoded: return "get_island"
        return "unknown"
    except:
        return "error"

def build_sfs_packet(data_dict):
    """Empaqueta la respuesta en el formato binario exacto que espera MSM"""
    payload = json.dumps(data_dict).encode('utf-8')
    # Encabezado SmartFox de 4 bytes: [2 bytes de tamaño] + [2 bytes de control de versión]
    header = len(payload).to_bytes(2, byteorder='big') + b'\x00\x01'
    return header + payload

# --- MANEJADORES DE SOLICITUDES DIRECTOS ---
def process_request(request_type):
    """Devuelve los datos exactos que el juego original necesita para cargar"""
    if request_type == "handshake":
        return {"success": True, "sessionToken": "msm_py_lite_99", "protocolVersion": "2.13.0"}
    
    elif request_type == "login":
        return {"success": True, "player": DATA_BASE["user_profile"]}
        
    elif request_type == "get_island":
        return {"success": True, "islands": DATA_BASE["islands"]}
        
    return {"success": False, "error": "Acción no reconocida"}

# --- NÚCLEO ASÍNCRONO DEL SERVIDOR ---
async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"[+] Conexión directa desde {addr}")
    
    try:
        while True:
            # Lee los primeros 2 bytes para determinar el tamaño del paquete
            header = await reader.read(2)
            if not header or len(header) < 2:
                break
                
            packet_size = int.from_bytes(header, byteorder='big')
            # Lee el resto del paquete (+2 bytes de control SFS)
            payload = await reader.read(packet_size + 2)
            
            # Procesar y responder inmediatamente
            req_type = parse_sfs_packet(payload)
            print(f"[*] Solicitud detectada: {req_type}")
            
            response_data = process_request(req_type)
            packet_to_send = build_sfs_packet(response_data)
            
            writer.write(packet_to_send)
            await writer.drain()
            
    except Exception as e:
        print(f"[-] Error en la conexión {addr}: {e}")
    finally:
        print(f"[-] Conexión cerrada con {addr}")
        writer.close()
        await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    print(f"🚀 Servidor MSM Ultra-Lite escuchando en {HOST}:{PORT}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
