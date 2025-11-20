import asyncio
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusDeviceContext, ModbusServerContext

# Configuración del PLC
# Coil 0 (Bobina): Estado de la Bomba (0 = OFF, 1 = ON)
# Holding Register 0: Nivel del agua (0 a 100)
store = ModbusDeviceContext(
    di=ModbusSequentialDataBlock(0, [0]*100),
    co=ModbusSequentialDataBlock(0, [0]*100), # Bobinas (Bomba)
    hr=ModbusSequentialDataBlock(0, [0]*100), # Registros (Nivel Agua)
    ir=ModbusSequentialDataBlock(0, [0]*100))

# En pymodbus 3.x, si single=False, se pasa un mapeo de device_id -> contexto
DEVICE_ID = 1
context = ModbusServerContext(devices={DEVICE_ID: store}, single=False)

async def simulacion_fisica():
    """Simula el comportamiento físico del tanque en segundo plano"""
    print("--- INICIANDO SIMULACIÓN DEL TANQUE ---")
    nivel_agua = 50
    
    while True:
        # Leer estado actual de la bomba (Coil 0) del 'contexto' (memoria del PLC)
        slave_id = 0x00
        bomba_activa = store.getValues(1, 0, count=1)[0]
        
        # Lógica física:
        # Si la bomba está ON (True), el agua baja.
        # Si la bomba está OFF (False), el agua sube (se llena).
        if bomba_activa:
            nivel_agua -= 2
        else:
            nivel_agua += 2
            
        # Límites físicos
        if nivel_agua < 0: nivel_agua = 0
        if nivel_agua > 100: nivel_agua = 100
        
        # Actualizar el sensor de nivel (Holding Register 0)
        store.setValues(3, 0, [nivel_agua])
        
        # Mostrar estado en la consola del servidor (opcional, para debug)
        estado_bomba = "ENCENDIDA (Drenando)" if bomba_activa else "APAGADA (Llenando)"
        # print(f"[PLC INTERNO] Nivel: {nivel_agua}% | Bomba: {estado_bomba}")
        
        await asyncio.sleep(1)

async def main():
    # Arrancamos la simulación física y el servidor Modbus simultáneamente
    task_sim = asyncio.create_task(simulacion_fisica())
    task_server = StartAsyncTcpServer(context=context, address=("localhost", 5020))
    await asyncio.gather(task_sim, task_server)

if __name__ == "__main__":
    asyncio.run(main())
