#!/bin/bash
set -e

# Detect PostgreSQL major version (e.g., 16)
PG_MAJOR=$(psql -V | awk '{print $3}' | cut -d. -f1)

# Initialize the PostgreSQL database cluster if it does not exist
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "Initializing PostgreSQL database cluster at $PGDATA..."
  su - postgres -c "/usr/lib/postgresql/$PG_MAJOR/bin/initdb -D '$PGDATA'"
fi

# Start PostgreSQL server in the background
echo "Starting PostgreSQL server..."
su - postgres -c "/usr/lib/postgresql/$PG_MAJOR/bin/pg_ctl -D '$PGDATA' -l '$PGDATA/logfile' start"

# Wait for PostgreSQL to become ready
echo "Waiting for PostgreSQL to be available..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  sleep 1
done

# Ensure PostgreSQL user and database exist
echo "Ensuring PostgreSQL user and database exist..."
su - postgres -c "psql -v ON_ERROR_STOP=1 --dbname=postgres" <<EOSQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$POSTGRES_USER') THEN
        CREATE USER "$POSTGRES_USER" WITH PASSWORD '$POSTGRES_PASSWORD';
    END IF;
END
\$\$;
EOSQL

# Ensure database exists
if ! su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname = '$POSTGRES_DB'\"" | grep -q 1; then
  su - postgres -c "createdb -O \"$POSTGRES_USER\" \"$POSTGRES_DB\""
fi

# Check if PostGIS control file exists
POSTGIS_CONTROL_FILE="/usr/share/postgresql/$PG_MAJOR/extension/postgis.control"
if [ ! -f "$POSTGIS_CONTROL_FILE" ]; then
  echo "WARNING: PostGIS extension is not available. Skipping installation."
else
  echo "Installing PostGIS and PostGIS Topology..."

  su - postgres -c "psql -v ON_ERROR_STOP=1 --dbname=$POSTGRES_DB" <<EOSQL
-- Create schemas
CREATE SCHEMA IF NOT EXISTS shared_extensions;
CREATE SCHEMA IF NOT EXISTS topology;

-- Install extensions
CREATE EXTENSION IF NOT EXISTS postgis SCHEMA shared_extensions;
CREATE EXTENSION IF NOT EXISTS postgis_topology SCHEMA topology;
EOSQL

  echo "Setting search_path to public, shared_extensions, topology..."
  su - postgres -c "psql -v ON_ERROR_STOP=1 --dbname=postgres -c \"ALTER DATABASE \\\"$POSTGRES_DB\\\" SET search_path = public,shared_extensions,topology;\""
fi

# Run custom SQL script if it exists
if [ -f "/app/simulation/data/script.sql" ]; then
  echo "Running SQL script /app/simulation/data/script.sql..."
  su - postgres -c "psql -v ON_ERROR_STOP=1 --dbname=$POSTGRES_DB -f /app/simulation/data/script.sql"
fi

# Keep container running (optionally run your app here)
exec /bin/bash