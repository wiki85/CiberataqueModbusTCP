import asyncio
import time
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusDeviceContext, ModbusServerContext

# Configuración del PLC
# Coil 0 (Bobina): Estado reportado de la Bomba (0 = OFF, 1 = ON) - la bomba llena el tanque
# Coil 1 (Bobina): Estado reportado de la Válvula (0 = Cerrada, 1 = Abierta) - la válvula vacía el tanque
# Coil 2 (Bobina): Forzar sensor externo (1 = no actualizar HR 0 desde la física, se permite spoofing)
# Coil 3 (Bobina): Forzar actuadores físicos (1 = la física usa bobinas dedicadas y no las públicas 0/1)
# Coil 10 (Bobina): Estado físico de la Bomba (usado por la simulación si está activa la forzación)
# Coil 11 (Bobina): Estado físico de la Válvula (usado por la simulación si está activa la forzación)
# Coil 12 (Bobina): Heartbeat de forzado; si no cambia en un tiempo, se desactiva el forzado
# Holding Register 0: Nivel del agua (0 a 100)
store = ModbusDeviceContext(
    di=ModbusSequentialDataBlock(0, [0]*100),
    co=ModbusSequentialDataBlock(0, [0]*100), # Bobinas (Bomba/Válvula)
    hr=ModbusSequentialDataBlock(0, [0]*100), # Registros (Nivel Agua)
    ir=ModbusSequentialDataBlock(0, [0]*100))

# En pymodbus 3.x, si single=False, se pasa un mapeo de device_id -> contexto
DEVICE_ID = 1
context = ModbusServerContext(devices={DEVICE_ID: store}, single=False)

async def simulacion_fisica():
    """Simula el comportamiento físico del tanque en segundo plano"""
    print("--- INICIANDO SIMULACIÓN DEL TANQUE ---")
    nivel_agua = 50
    COIL_BOMBA = 0
    COIL_VALVULA = 1
    COIL_FORZAR_SENSOR = 2
    COIL_FORZAR_ACT = 3
    COIL_BOMBA_REAL = 10
    COIL_VALVULA_REAL = 11
    COIL_FORZAR_HB = 12
    hb_last_state = 0
    hb_last_time = 0
    
    while True:
        # Leer estado actual de la bomba y la válvula (pública y, si aplica, forzada)
        forzar_act_flag = store.getValues(1, COIL_FORZAR_ACT, count=1)[0]
        hb_state = store.getValues(1, COIL_FORZAR_HB, count=1)[0]
        if hb_state != hb_last_state:
            hb_last_state = hb_state
            hb_last_time = time.time()

        override_alive = forzar_act_flag and (time.time() - hb_last_time <= 2)
        if not override_alive and forzar_act_flag:
            # Sin heartbeat: desactivar forzados
            store.setValues(1, COIL_FORZAR_ACT, [0])
            store.setValues(1, COIL_FORZAR_SENSOR, [0])
            override_alive = False

        if override_alive:
            bomba_activa = store.getValues(1, COIL_BOMBA_REAL, count=1)[0]
            valvula_abierta = store.getValues(1, COIL_VALVULA_REAL, count=1)[0]
        else:
            bomba_activa = store.getValues(1, COIL_BOMBA, count=1)[0]
            valvula_abierta = store.getValues(1, COIL_VALVULA, count=1)[0]
            # Reflejar estado físico en las bobinas dedicadas
            store.setValues(1, COIL_BOMBA_REAL, [bomba_activa])
            store.setValues(1, COIL_VALVULA_REAL, [valvula_abierta])
        forzar_sensor = store.getValues(1, COIL_FORZAR_SENSOR, count=1)[0]
        
        # Lógica física:
        # La bomba llena el tanque, la válvula lo vacía. Si ambas están activas, se compensan.
        if bomba_activa:
            nivel_agua += 2
        if valvula_abierta:
            nivel_agua -= 2
            
        # Límites físicos
        if nivel_agua < 0: nivel_agua = 0
        if nivel_agua > 100: nivel_agua = 100
        
        # Actualizar el sensor de nivel (Holding Register 0) solo si no está forzado externamente
        if not forzar_sensor:
            store.setValues(3, 0, [nivel_agua])
        
        # Mostrar estado en la consola del servidor (opcional, para debug)
        estado_bomba = "ENCENDIDA (Llenando)" if bomba_activa else "APAGADA"
        estado_valvula = "ABIERTA (Vaciando)" if valvula_abierta else "CERRADA"
        # print(f"[PLC INTERNO] Nivel: {nivel_agua}% | Bomba: {estado_bomba} | Válvula: {estado_valvula}")
        
        await asyncio.sleep(1)

async def main():
    # Arrancamos la simulación física y el servidor Modbus simultáneamente
    task_sim = asyncio.create_task(simulacion_fisica())
    task_server = StartAsyncTcpServer(context=context, address=("localhost", 5020))
    await asyncio.gather(task_sim, task_server)

if __name__ == "__main__":
    asyncio.run(main())
