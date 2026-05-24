#!/usr/bin/env sh
set -e

TEST_DB_NAME="${TEST_DB_NAME:-test_db}"

psql -v ON_ERROR_STOP=1 -v test_db_name="$TEST_DB_NAME" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE "' || :'test_db_name' || '"'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'test_db_name')\gexec
EOSQL
