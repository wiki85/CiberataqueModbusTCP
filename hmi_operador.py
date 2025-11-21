import time
import curses
from pymodbus.client import ModbusTcpClient

DEVICE_ID = 1          # Coincide con el contexto del servidor (PLC)
HOST = "localhost"
PORT = 5020
HIGH_LIMIT = 90        # Umbral alto: forzar bomba OFF
LOW_LIMIT = 10         # Umbral bajo: forzar bomba ON
REFRESH_SECS = 0.2     # Frecuencia de refresco de la HMI
COIL_BOMBA = 0         # Bobina de la bomba de llenado
COIL_VALVULA = 1       # Bobina de la válvula de vaciado


def render(stdscr, nivel, bomba, valvula, info, auto_info):
    """Dibuja la UI en pantalla fija (sin despejar la consola)."""
    stdscr.erase()
    stdscr.addstr(0, 0, "=== SISTEMA SCADA: CONTROL DE TANQUE ===")
    stdscr.addstr(1, 0, f"Conexión: {HOST}:{PORT} | Dispositivo: {DEVICE_ID} | Protocolo: Modbus TCP")
    stdscr.addstr(2, 0, "-" * 60)

    # Barra del tanque (50 chars)
    barras = "█" * max(0, min(50, nivel // 2))
    espacios = " " * (50 - len(barras))
    estado = "NORMAL"
    critico = False
    if nivel >= HIGH_LIMIT:
        estado = "¡PELIGRO! NIVEL ALTO"
        critico = True
    elif nivel <= LOW_LIMIT:
        estado = "NIVEL BAJO"
        critico = True

    barra_color = curses.color_pair(2 if critico else 1)
    stdscr.addstr(3, 0, "NIVEL DE AGUA: ")
    stdscr.addstr(f"[{barras}{espacios}] {nivel:3}%", barra_color)
    stdscr.addstr(4, 0, f"ESTADO: {estado}")
    stdscr.addstr(5, 0, f"BOMBA:   {'[ ON ] Llenando' if bomba else '[ OFF ] Detenida'}")
    stdscr.addstr(6, 0, f"VÁLVULA: {'[ ABIERTA ] Vaciando' if valvula else '[ CERRADA ] Sin vaciado'}")
    stdscr.addstr(7, 0, "-" * 60)
    stdscr.addstr(8, 0, f"Auto: {auto_info}")
    stdscr.addstr(9, 0, f"Info: {info}")
    stdscr.addstr(10, 0, "-" * 60)
    stdscr.addstr(11, 0, "Controles: Bomba [o]=ON [p]=OFF [t]=Toggle | Válvula [a]=Abrir [c]=Cerrar [v]=Toggle | [q]=Salir")
    stdscr.refresh()


def main(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)  # Barra normal (llenado seguro)
    curses.init_pair(2, curses.COLOR_RED, -1)    # Barra en límite crítico
    stdscr.nodelay(True)

    client = ModbusTcpClient(HOST, port=PORT)
    if not client.connect():
        raise SystemExit(f"No se pudo conectar al PLC en {HOST}:{PORT}")

    nivel_actual = 0
    bomba_actual = False
    valvula_abierta = False
    info = "HMI iniciado"
    auto_info = "Esperando lectura"

    try:
        while True:
            # Entrada no bloqueante
            key = stdscr.getch()
            if key in (ord("q"), ord("Q")):
                break
            if key in (ord("o"), ord("O")):
                client.write_coil(COIL_BOMBA, True, device_id=DEVICE_ID)
                info = "Bomba encendida manualmente"
            elif key in (ord("p"), ord("P")):
                client.write_coil(COIL_BOMBA, False, device_id=DEVICE_ID)
                info = "Bomba apagada manualmente"
            elif key in (ord("t"), ord("T")):
                client.write_coil(COIL_BOMBA, not bomba_actual, device_id=DEVICE_ID)
                info = f"Bomba {'encendida' if not bomba_actual else 'apagada'} manualmente (toggle)"
            elif key in (ord("a"), ord("A")):
                client.write_coil(COIL_VALVULA, True, device_id=DEVICE_ID)
                info = "Válvula abierta manualmente"
            elif key in (ord("c"), ord("C")):
                client.write_coil(COIL_VALVULA, False, device_id=DEVICE_ID)
                info = "Válvula cerrada manualmente"
            elif key in (ord("v"), ord("V")):
                client.write_coil(COIL_VALVULA, not valvula_abierta, device_id=DEVICE_ID)
                info = f"Válvula {'abierta' if not valvula_abierta else 'cerrada'} manualmente (toggle)"

            # Lectura de sensores
            rr = client.read_holding_registers(0, count=1, device_id=DEVICE_ID)
            rc = client.read_coils(0, count=2, device_id=DEVICE_ID)

            if rr.isError() or rc.isError():
                info = f"Error de lectura: rr={rr} rc={rc}"
                auto_info = "Sin datos"
            else:
                nivel_actual = rr.registers[0]
                bomba_actual = rc.bits[COIL_BOMBA]
                valvula_abierta = rc.bits[COIL_VALVULA]

                # Lógica automática: la bomba llena, nunca vacía.
                if nivel_actual <= LOW_LIMIT and not bomba_actual:
                    client.write_coil(COIL_BOMBA, True, device_id=DEVICE_ID)
                    auto_info = f"AUTO: Nivel <= {LOW_LIMIT}%, bomba ON (llenando)"
                elif nivel_actual >= HIGH_LIMIT and bomba_actual:
                    client.write_coil(COIL_BOMBA, False, device_id=DEVICE_ID)
                    auto_info = f"AUTO: Nivel >= {HIGH_LIMIT}%, bomba OFF"
                else:
                    auto_info = "AUTO: en rango (válvula manual)"

            render(stdscr, nivel_actual, bomba_actual, valvula_abierta, info, auto_info)
            time.sleep(REFRESH_SECS)
    finally:
        client.close()


if __name__ == "__main__":
    curses.wrapper(main)
