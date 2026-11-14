# Backend & Demo Progress (`agrofarm-api` & `agrofarm-docs`)

| Block | Issue | PR | Status | Notes |
|---|---|---|---|---|
| Block 1 | `agrofarm-docs#13` (DEC-005) | [agrofarm-docs#24](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-docs/pull/24) | PR open | Farm upload schema (CSV + GeoJSON) + valid/invalid examples with provisional Guatemala City polygon. |
| Block 1 | `agrofarm-api#4` (BE-015) | [agrofarm-api#23](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/23) | PR open | ADR `0001-farm-polygons-storage.md` choosing `jsonb` GeoJSON for MVP. |
| Block 2 | `agrofarm-api#9` (BE-020), `#10` (BE-025) | [agrofarm-api#24](https://github.com/Quetzpaciales-Space-Apps-Team/agrofarm-api/pull/24) | PR open | Farms CRUD + pagination + EPSG:4326 polygon validation + IDOR checks + priorities/constraints + migration 0002. |
| Block 3 | `agrofarm-api#6` (BE-010) | In progress | PR opening | Auth MVP (`/register`, `/login`, `/refresh`, `/logout`, `/me`) + migration 0003; reuse-detection family revocation & rate-limit deferred post-MVP. |
