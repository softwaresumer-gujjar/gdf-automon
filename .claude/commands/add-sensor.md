# /add-sensor — Interactive Sensor Addition Wizard

Walk the user through adding a new sensor to the GDF-AutoMon system step by step.

## Steps

1. **Fetch available sensor types** from the backend registry:
   ```bash
   curl -s http://localhost:8000/api/sensors/types | python -m json.tool
   ```

2. **Present sensor types** to the user and ask them to pick one.

3. **Show the config schema** for the chosen type and ask the user to provide values for each required field.

4. **Test the connection** (if the sensor is reachable):
   ```bash
   cd backend && python -c "
   from app.plugins.registry import registry
   import asyncio, json
   config = $CONFIG_JSON
   adapter = registry.create('$SENSOR_TYPE', config)
   asyncio.run(adapter.connect(config))
   print('Connection OK')
   "
   ```

5. **Save the sensor** to the database:
   ```bash
   curl -s -X POST http://localhost:8000/api/sensors \
     -H 'Content-Type: application/json' \
     -d '$SENSOR_PAYLOAD' | python -m json.tool
   ```

6. **Confirm** the sensor appears on the dashboard at http://localhost:5173

## Notes
- MQTT sensors need the ESP32/RPi device to be publishing to `gdf/{sensor_id}/{channel}`
- Modbus sensors need the device IP/port and register map
- Camera sensors need the RTSP URL (e.g. `rtsp://admin:pass@192.168.1.10:554/stream`)
