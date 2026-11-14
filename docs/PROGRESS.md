# Backend & Demo Progress (`agrofarm-api` & `agrofarm-docs`)

| Block | Issue | PR | Status | Notes |
|---|---|---|---|---|
| Block 1 | `agrofarm-docs#13` (DEC-005) | [agrofarm-docs#24](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-docs/pull/24) | PR open | Farm upload schema (CSV + GeoJSON) + valid/invalid examples with provisional Guatemala City polygon. |
| Block 1 | `agrofarm-api#4` (BE-015) | [agrofarm-api#23](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/23) | PR open | ADR `0001-farm-polygons-storage.md` choosing `jsonb` GeoJSON for MVP. |
| Block 2 | `agrofarm-api#9` (BE-020), `#10` (BE-025) | [agrofarm-api#24](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/24) | PR open | Farms CRUD + pagination + EPSG:4326 polygon validation + IDOR checks + priorities/constraints + migration 0002. |
| Block 3 | `agrofarm-api#6` (BE-010) | [agrofarm-api#25](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/25) | PR open | Auth MVP (`/register`, `/login`, `/refresh`, `/logout`, `/me`) + migration 0003; reuse-detection family revocation & rate-limit deferred post-MVP. |
| Block 4 | `agrofarm-api#11` (BE-030) | [agrofarm-api#26](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/26) | PR open | Farm CSV/GeoJSON uploads following DEC-005, streaming 413 check, row-level errors, CSV escape helper, migration 0004. |
| Block 5 | `agrofarm-api#7` (BE-045), `#14` (BE-050) | In progress | PR opening | `MLClient` (`ML_MODE=fixture|http`), `/v1/climate/enso`, `/v1/scenarios/simulate`, `/v1/farms/{id}/recommendations` with provenance & migration 0005. |
