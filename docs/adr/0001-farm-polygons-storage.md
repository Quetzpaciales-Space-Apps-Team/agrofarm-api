# 0001. Farm Polygons Storage: PostGIS vs GeoJSON in `jsonb`

- Status: accepted (MVP decision by Person 6 under hackathon time constraint)
- Date: 2026-11-14
- Deciders: Person 6 (Backend, integration and demo)

## Context

`core-api` needs to store farm polygons (`EPSG:4326`, RFC 7946 GeoJSON) and support farm CRUD (`BE-020`), uploads (`BE-030`), and centroid/bounding-box queries. The current `docker-compose.yml` uses `pgvector/pgvector:pg17`, which includes `pgvector` and `pg_trgm` but does not include PostGIS.

## Options

1. **PostGIS (`geometry(Geometry, 4326)` + GeoAlchemy2)**
   - Pros: Native spatial indexes (`GIST`), `ST_Area`, `ST_Intersects`, `ST_IsValid` in SQL.
   - Cons: Requires replacing `pgvector/pgvector:pg17` in `docker-compose.yml` (or building a custom image with both `pgvector` and `postgis`), enabling the `postgis` extension in Cloud SQL, and adding `geoalchemy2`/`shapely` system dependencies (`libgeos`).
2. **GeoJSON in PostgreSQL `jsonb` + application-level EPSG:4326 validation**
   - Pros: Zero changes to `pgvector/pgvector:pg17` or Cloud SQL extensions; zero C-library build risks in `Dockerfile`; stores the exact RFC 7946 GeoJSON Polygon/MultiPolygon received from the frontend and uploads; trivial to serialize/deserialize in FastAPI.
   - Cons: Spatial intersection queries in SQL are not indexed with `GIST` (not required for MVP); area/centroid are computed in Python at write time and stored as numeric columns (`area_ha`, `centroid_lat`, `centroid_lon`).

## Decision

Choose **Option 2: GeoJSON in `jsonb`** (plus precomputed `area_ha`, `centroid_lat`, `centroid_lon` columns) for the hackathon MVP.

## Consequences

- **Local compose impact:** None. `pgvector/pgvector:pg17` remains unchanged.
- **Cloud SQL impact:** None. No extra extension (`postgis`) needs to be enabled or managed in Cloud SQL.
- **Migration path:** If spatial joins across thousands of farms are needed post-hackathon, a migration can add a `geom geometry(MultiPolygon, 4326)` column populated from the `jsonb` payload via `ST_GeomFromGeoJSON`.
