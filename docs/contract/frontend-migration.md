# Frontend Contract Migration Guide (`agrofarm-api` -> `agrofarm-frontend`)

**Decision:** `agrofarm-api/docs/contract/openapi.yaml` is the single source of truth for the REST API. This guide documents every discrepancy between the current `agrofarm-frontend` types/MSW handlers (`schema.d.ts`, `src/test/handlers.ts`) and `core-api`, plus the exact steps to align them.

---

## 1. Field-by-Field Mapping (Frontend Current -> `core-api`)

### 1.1 Path Parameters
| Frontend (`schema.d.ts` / `handlers.ts`) | `core-api` (Source of Truth) | Notes |
|---|---|---|
| `/v1/farms/{id}` | `/v1/farms/{farm_id}` | Update path param name in OpenAPI & generated types. |
| `/v1/farms/{id}/uploads` | `/v1/farms/{farm_id}/uploads` | Same. |
| `/v1/farms/{id}/priorities` | `/v1/farms/{farm_id}/priorities` | Same. |
| `/v1/farms/{id}/insights` | `/v1/farms/{farm_id}/insights` | Same. |
| `/v1/farms/{id}/recommendations` | `/v1/farms/{farm_id}/recommendations` | Same. |

### 1.2 `GET /v1/me` (`UserProfile` -> `User`)
| Frontend Field | `core-api` Field | Type / Format | Action in Frontend |
|---|---|---|---|
| `full_name` | `name` | `string` | Rename `full_name` -> `name`. |
| `id`, `email`, `role`, `created_at` | `id`, `email`, `role`, `created_at` | `uuid` / `string` / `date-time` | Keep (`id` is UUID string). |

### 1.3 `GET / POST /v1/farms` & `/v1/farms/{farm_id}` (`Farm`)
| Frontend Field | `core-api` Field | Type / Unit / Notes | Action in Frontend |
|---|---|---|---|
| `polygon` | `boundary` | GeoJSON Polygon (`EPSG:4326`) | Rename `polygon` -> `boundary`. |
| `reference_point: {latitude, longitude}` | `centroid_lat`, `centroid_lon` | `number` (EPSG:4326 degrees) | Read top-level `centroid_lat` and `centroid_lon`. |
| `area_ha`, `current_rotation`, `name`, `id`, `created_at` | `area_ha`, `current_rotation`, `name`, `id`, `created_at` | `ha`, `string[]` | Keep. |
| `department`, `municipality`, `elevation_m`, `station_reference`, `updated_at` | *(not returned in MVP)* | — | Remove from required UI/types or treat as optional/omitted. |

### 1.4 `GET /v1/climate/enso` (`EnsoSeriesResponse` -> `EnsoSeries`)
| Frontend Field | `core-api` Field | Type / Unit / Notes | Action in Frontend |
|---|---|---|---|
| `items[].oni_c` | `items[].oni` | `number \| null` (°C) | Rename `oni_c` -> `oni`. |
| `items[].roni_c` | `items[].roni` | `number \| null` (°C) | Rename `roni_c` -> `roni`. |
| `items[].rainfall_anomaly_note` | *(not in `core-api`)* | — | Remove or compute client-side hint from `phase`. |
| `provenance` | *(not in `EnsoSeries`; `source` string instead)* | `source: string` | Use `source` + `disclaimer` (both returned by `core-api`). |
| `disclaimer` | `disclaimer` | `string` | Keep; always present in `core-api`. |
| `threshold_c`, `items[].month`, `items[].phase` | `threshold_c`, `items[].month`, `items[].phase` | `0.5`, `YYYY-MM`, `el_nino \| la_nina \| neutral` | Keep. |

### 1.5 `POST /v1/scenarios/simulate` (`ScenarioSimulationResponse` -> `SimulationResult`)
| Frontend Field | `core-api` Field | Type / Unit / Notes | Action in Frontend |
|---|---|---|---|
| `crop_id` | `crop` | `string` | Rename `crop_id` -> `crop`. |
| `metric_name` | `target` | `string` (e.g. `yield_anomaly_pct`) | Rename `metric_name` -> `target`. |
| `baseline.unit`, `scenario.unit` | Top-level `unit` | `string` (`%` in `core-api`, vs `kg/ha` in MSW stub) | Read top-level `unit` (`%` yield anomaly). |
| `baseline.confidence_note`, `scenario.confidence_note` | *(not in `QuantileRange`)* | `{p10, p50, p90}` (`p10 <= p50 <= p90`) | Remove `confidence_note` from `QuantileRange`. |
| `out_of_training_range`, `range_warning` | `out_of_range_inputs` | `string[]` | Derive boolean `out_of_range_inputs.length > 0`. |
| `top_attributions: [{feature, shap_value, direction, explanation}]` | `attributions: [{feature, contribution}]` | `number` (`%` contribution) | Rename to `attributions`; derive direction from `contribution >= 0`. |
| `timeline` | *(not returned in MVP)* | — | Remove or hide timeline chart until post-MVP. |
| `provenance`, `disclaimer` | `provenance`, `disclaimer` | See `Provenance` below | Keep. |

### 1.6 `POST /v1/farms/{farm_id}/recommendations` (`Recommendation` -> `RecommendationSet`)
| Frontend Field | `core-api` Field | Scale / Type / Notes | Action in Frontend |
|---|---|---|---|
| `scenario_summary` | *(not returned)* | — | Display active scenario inputs from UI state. |
| `strategies[].is_current_rotation` | `strategies[].is_current` | `boolean` | Rename `is_current_rotation` -> `is_current`. |
| `strategies[].evidence` (`string[]`) | `strategies[].evidence` (`{statement, source}[]`) | Array of objects | Render `item.statement` + `item.source` badge. |
| `strategies[].risks` (`string[]`) | `strategies[].risks` (`{description, needs_local_review}[]`) | Array of objects | Render `item.description` + review badge. |
| `strategies[].uncertainty: {p10, p50, p90, unit, confidence_note}` | `strategies[].uncertainty: {low, high}` | Normalized **`0–1`** interval | Display `low`–`high` interval (or multiply by 100 for %). |
| `strategies[].scores: {overall, yield_stability, soil_health, water_efficiency, income_diversification, low_input_cost}` (**0–100**) | `strategies[].overall_score` + `scores: {water_use, income, soil_structure, forage_value, nitrogen_fixing, erosion_reduction, market_suitability}` (**0–1**) | **Scale `0–1`** (`core-api`) vs `0–100` (MSW) | Read `overall_score` and the 7 `0–1` priority keys; multiply by `100` in UI if showing percentages. |
| `provenance.data_versions` (array of objects) | `provenance.data_versions` (`Record<string, string>`) | `dict[str, str]` | Iterate `Object.entries(provenance.data_versions)`. |
| `provenance` (`model_name`, `model_version`, `data_versions`, `input_hash`, `generated_at`) | Same 5 keys | All `string` / `Record<string, string>` | Keep. |

---

## 2. Exact Steps to Update `agrofarm-frontend`

1. Copy the canonical OpenAPI contract from `agrofarm-api`:
   ```bash
   cp ../agrofarm-api/docs/contract/openapi.yaml docs/contract/openapi.yaml
   ```
2. Regenerate TypeScript schema types (`src/infrastructure/api/schema.d.ts`):
   ```bash
   npx openapi-typescript docs/contract/openapi.yaml -o src/infrastructure/api/schema.d.ts
   ```
3. Update `src/test/handlers.ts` and `src/test/handlers.test.ts` so all MSW fixtures match `components['schemas']` from the regenerated `schema.d.ts` (including `0–1` score scale, `boundary`, `oni`/`roni`, `attributions`, `evidence` objects, `risks` objects, `data_versions` dictionary, and `disclaimer`).
4. Verify locally in `agrofarm-frontend`:
   ```bash
   npm run typecheck && npm run lint && npm test && npm run build
   ```
