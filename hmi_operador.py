import time
import curses
from pymodbus.client import ModbusTcpClient

DEVICE_ID = 1          # Coincide con el contexto del servidor (PLC)
HOST = "localhost"
PORT = 5020
HIGH_LIMIT = 90        # Umbral alto: forzar bomba ON
LOW_LIMIT = 10         # Umbral bajo: forzar bomba OFF
REFRESH_SECS = 0.5     # Frecuencia de refresco de la HMI


def render(stdscr, nivel, bomba, info, auto_info):
    """Dibuja la UI en pantalla fija (sin despejar la consola)."""
    stdscr.erase()
    stdscr.addstr(0, 0, "=== SISTEMA SCADA: CONTROL DE TANQUE ===")
    stdscr.addstr(1, 0, f"Conexión: {HOST}:{PORT} | Dispositivo: {DEVICE_ID} | Protocolo: Modbus TCP")
    stdscr.addstr(2, 0, "-" * 60)

    # Barra del tanque (50 chars)
    barras = "█" * max(0, min(50, nivel // 2))
    espacios = " " * (50 - len(barras))
    estado = "NORMAL"
    if nivel >= HIGH_LIMIT:
        estado = "¡PELIGRO! NIVEL ALTO"
    elif nivel <= LOW_LIMIT:
        estado = "NIVEL BAJO"
    stdscr.addstr(3, 0, f"NIVEL DE AGUA: [{barras}{espacios}] {nivel:3}%")
    stdscr.addstr(4, 0, f"ESTADO: {estado}")
    stdscr.addstr(5, 0, f"BOMBA: {'[ ON ] Drenando' if bomba else '[ OFF ] Detenida'}")
    stdscr.addstr(6, 0, "-" * 60)
    stdscr.addstr(7, 0, f"Auto: {auto_info}")
    stdscr.addstr(8, 0, f"Info: {info}")
    stdscr.addstr(9, 0, "-" * 60)
    stdscr.addstr(10, 0, "Controles: [o]=Bomba ON  [p]=Bomba OFF  [t]=Toggle  [q]=Salir")
    stdscr.refresh()


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)

    client = ModbusTcpClient(HOST, port=PORT)
    if not client.connect():
        raise SystemExit(f"No se pudo conectar al PLC en {HOST}:{PORT}")

    nivel_actual = 0
    bomba_actual = False
    info = "HMI iniciado"
    auto_info = "Esperando lectura"

    try:
        while True:
            # Entrada no bloqueante
            key = stdscr.getch()
            if key in (ord("q"), ord("Q")):
                break
            if key in (ord("o"), ord("O")):
                client.write_coil(0, True, device_id=DEVICE_ID)
                info = "Bomba encendida manualmente"
            elif key in (ord("p"), ord("P")):
                client.write_coil(0, False, device_id=DEVICE_ID)
                info = "Bomba apagada manualmente"
            elif key in (ord("t"), ord("T")):
                client.write_coil(0, not bomba_actual, device_id=DEVICE_ID)
                info = f"Bomba {'encendida' if not bomba_actual else 'apagada'} manualmente (toggle)"

            # Lectura de sensores
            rr = client.read_holding_registers(0, count=1, device_id=DEVICE_ID)
            rc = client.read_coils(0, count=1, device_id=DEVICE_ID)

            if rr.isError() or rc.isError():
                info = f"Error de lectura: rr={rr} rc={rc}"
                auto_info = "Sin datos"
            else:
                nivel_actual = rr.registers[0]
                bomba_actual = rc.bits[0]

                # Lógica automática
                if nivel_actual >= HIGH_LIMIT and not bomba_actual:
                    client.write_coil(0, True, device_id=DEVICE_ID)
                    auto_info = f"AUTO: Nivel >= {HIGH_LIMIT}%, bomba ON"
                elif nivel_actual <= LOW_LIMIT and bomba_actual:
                    client.write_coil(0, False, device_id=DEVICE_ID)
                    auto_info = f"AUTO: Nivel <= {LOW_LIMIT}%, bomba OFF"
                else:
                    auto_info = "AUTO: en rango"

            render(stdscr, nivel_actual, bomba_actual, info, auto_info)
            time.sleep(REFRESH_SECS)
    finally:
        client.close()


if __name__ == "__main__":
    curses.wrapper(main)
