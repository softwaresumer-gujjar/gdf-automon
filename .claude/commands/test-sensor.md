# /test-sensor — Live Sensor Connection Test

Connect to a sensor and stream its readings to stdout for 30 seconds.

## Steps

1. List sensors in the database:
   ```bash
   curl -s http://localhost:8000/api/sensors | python -m json.tool
   ```

2. Ask the user to pick a sensor by ID or name.

3. Stream live readings for 30 seconds:
   ```bash
   curl -s -N "http://localhost:8000/api/stream/sensor/{sensor_id}" 
   ```
   (This hits the SSE endpoint — each line is a JSON reading)

4. If the sensor is not producing data, check:
   - MQTT: subscribe directly to see if device is publishing
     ```bash
     docker exec -it gdf-emqx bin/emqx_ctl subscribe gdf/{sensor_id}/#
     ```
   - Sensor status in DB:
     ```bash
     docker exec -it gdf-timescaledb psql -U gdf gdfautomon -c \
       "SELECT id, name, status, config FROM sensors WHERE id = '{sensor_id}';"
     ```
   - Backend logs:
     ```bash
     docker logs --tail 50 gdf-backend
     ```
