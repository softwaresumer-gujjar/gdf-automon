# /gen-sensor-type — Scaffold a New Sensor Type

Generate all boilerplate files needed to add a new sensor type to GDF-AutoMon.

## Steps

1. Ask the user for:
   - **Sensor type name** (snake_case, e.g. `soil_moisture_v1`)
   - **Display name** (e.g. "Soil Moisture Sensor")
   - **Protocol** (`mqtt` | `modbus` | `serial` | `http`)
   - **Data channels** (list of: name, unit, value type — e.g. `moisture_pct`, `%`, `float`)
   - **Config fields** needed (e.g. for MQTT: topic prefix; for Modbus: ip, port, register)

2. Create `backend/app/plugins/types/{name}.py`:
   - Extend `SensorAdapter` from `backend/app/plugins/base.py`
   - Fill in `sensor_type`, `config_schema`, `data_channels`
   - Use the appropriate adapter from `backend/app/plugins/adapters/`

3. Register in `backend/app/plugins/registry.py`:
   - Import the new class
   - Call `registry.register(MySensorType)`

4. Create `sensor-edge/` script or firmware stub:
   - For MQTT sensors: create `sensor-edge/esp32/{name}/main.cpp` (Arduino template)
   - For Serial/RS-232: create `sensor-edge/raspberry-pi/{name}_bridge.py`

5. Restart backend to load the new type:
   ```bash
   docker compose restart backend
   ```

6. Verify it appears:
   ```bash
   curl http://localhost:8000/api/sensors/types
   ```

## Template Reference
See `backend/app/plugins/types/temperature.py` for a complete working example.
