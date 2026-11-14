-- Enable approved extensions only. PostGIS stays off until ADR BE-015.
DROP EXTENSION IF EXISTS postgis_tiger_geocoder CASCADE;
DROP EXTENSION IF EXISTS postgis_topology CASCADE;
DROP EXTENSION IF EXISTS postgis CASCADE;

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
