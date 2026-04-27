# /db-migrate — Run Database Migrations

Apply pending Alembic migrations to TimescaleDB.

## Steps

1. Check current migration state:
   ```bash
   docker exec -it gdf-backend alembic current
   ```

2. Show pending migrations:
   ```bash
   docker exec -it gdf-backend alembic history --indicate-current
   ```

3. Apply all pending migrations:
   ```bash
   docker exec -it gdf-backend alembic upgrade head
   ```

4. If running outside Docker (local dev):
   ```bash
   cd backend
   DATABASE_URL="postgresql+asyncpg://gdf:gdf_secure_2024@localhost:5432/gdfautomon" \
     alembic upgrade head
   ```

5. Verify hypertables were created:
   ```bash
   docker exec -it gdf-timescaledb psql -U gdf gdfautomon -c \
     "SELECT hypertable_name, num_chunks FROM timescaledb_information.hypertables;"
   ```

## Creating a New Migration
```bash
cd backend
alembic revision --autogenerate -m "description_of_change"
# Review the generated file in alembic/versions/
alembic upgrade head
```
