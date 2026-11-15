# Frontend Demo Flow Guide (Passwordless Judge Flow)

This guide defines the end-to-end integration flow for a Space Apps judge opening the public application in an incognito/private browser window without credentials (`FE-090` / `BE-090`). All examples below match [`openapi.yaml`](openapi.yaml) and the real `cached_demo` snapshots in [`examples/`](examples/).

- **Staging API Base URL:** `https://core-api-staging-7l2bzjrqpq-uc.a.run.app`
- **Staging Frontend URL:** `https://frontend-staging-7l2bzjrqpq-uc.a.run.app`
- **Required Global Disclaimer (must remain visible on climate, simulation, and recommendation views):**
  > `"This tool supports decisions. It does not replace farmers or local agronomists."`

---

## CORS, Cookies, Token Expiry & Error Handling

- **CORS & Cookies:** Send `credentials: "include"` on auth requests (`/v1/auth/demo`, `/v1/auth/refresh`, `/v1/auth/logout`). `core-api` sets an `httpOnly` cookie named `refresh_token` (`SameSite=Lax`).
  - Note: Across different `.run.app` origins (`frontend-staging-*.run.app` -> `core-api-staging-*.run.app`), browsers treat `SameSite=Lax` cookies as third-party on `fetch`; keep `access_token` in React memory for `Authorization: Bearer <token>` (valid for `expires_in: 900` seconds = 15 minutes). If a `401` occurs in cross-origin staging before custom domain `agrofarming.site` is active, re-calling `POST /v1/auth/demo` provisions a fresh guest session.
- **Error Format (`application/problem+json`):**
  - `401 Unauthorized`: Missing/expired Bearer token. Attempt `/v1/auth/refresh` (or re-run `POST /v1/auth/demo` for demo guests).
  - `422 Unprocessable Entity`: Request validation error (`detail` explains the invalid field/range). Display inline field errors.
  - `429 Too Many Requests`: Rate limit exceeded on `POST /v1/auth/demo` (`DEMO_RATE_LIMIT_PER_MINUTE=20` per IP). Show a friendly retry message.
  - `503 Service Unavailable`: Active demo guest cap (`DEMO_MAX_GUESTS=200`) or `ml-service` unreachable when `ML_MODE=http`.

---

## Step-by-Step Judge Flow

### 1. Start Passwordless Demo Session — `POST /v1/auth/demo`
- **Suggested Screen:** Landing / Hero (`"Try the demo"` CTA button; keep `"Sign in"` / `"Register"` links for real farm accounts).
- **Request:** No body required (`credentials: "include"`).
- **Response (`201 Created`):**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "expires_in": 900,
    "farm_id": "22222222-2222-4222-8222-222222222222",
    "is_demo_guest": true
  }
  ```
- **UI Actions:** Store `access_token` in memory, store `farm_id` and `is_demo_guest`, and navigate to the Farm Dashboard.

### 2. Load Guest Profile — `GET /v1/me`
- **Suggested Screen:** Top bar / Session badge (`"Demo Guest Session"`).
- **Response (`200 OK`):**
  ```json
  {
    "id": "0c858335-6b11-49fb-aaf0-bef827e1d03e",
    "email": "demo-guest-77f46394-1862-4981-bcd5-d69b6f8d7bf5@demo.agrofarm.invalid",
    "name": "Demo Guest",
    "role": "farmer",
    "created_at": "2026-11-15T06:54:23.257189Z"
  }
  ```

### 3. Load Provisional Pilot Farm — `GET /v1/farms/{farm_id}`
- **Suggested Screen:** Farm Map & Parcel Overview.
- **Fields to Show:** `name` (`"Guatemala Pilot Farm (Provisional)"`), `area_ha` (`ha`), `centroid_lat` / `centroid_lon`, `current_rotation` (`["maize", "beans"]`), `boundary` (GeoJSON Polygon in `EPSG:4326`, `[lon, lat]` order).
- **Response (`200 OK`):**
  ```json
  {
    "id": "22222222-2222-4222-8222-222222222222",
    "name": "Guatemala Pilot Farm (Provisional)",
    "boundary": {
      "type": "Polygon",
      "coordinates": [
        [
          [-90.515, 14.633],
          [-90.511, 14.633],
          [-90.511, 14.637],
          [-90.515, 14.637],
          [-90.515, 14.633]
        ]
      ]
    },
    "area_ha": 19.1,
    "centroid_lat": 14.635,
    "centroid_lon": -90.513,
    "current_rotation": ["maize", "beans"],
    "created_at": "2026-11-15T06:54:23.257189Z"
  }
  ```

### 4. Set Farmer Priorities & Constraints — `PUT /v1/farms/{farm_id}/priorities`
- **Suggested Screen:** Priorities & Constraints Form (7 sliders in `[0, 1]`).
- **Scales:** Each weight is a float `0.0` to `1.0` (`water_use`, `income`, `soil_structure`, `forage_value`, `nitrogen_fixing`, `erosion_reduction`, `market_suitability`). `water_availability` is `"low" | "medium" | "high"`; `equipment` is a string array.
- **Request:**
  ```json
  {
    "weights": {
      "water_use": 0.8,
      "income": 0.7,
      "soil_structure": 0.6,
      "forage_value": 0.2,
      "nitrogen_fixing": 0.7,
      "erosion_reduction": 0.8,
      "market_suitability": 0.6
    },
    "constraints": {
      "water_availability": "medium",
      "equipment": []
    }
  }
  ```
- **Response (`200 OK`):** Echoes the saved `weights` and `constraints` object.

### 5. Upload Farm Data (CSV or GeoJSON, `DEC-005`) — `POST /v1/farms/{farm_id}/uploads`
- **Suggested Screen:** Farm Data Upload Wizard (`multipart/form-data` with field `file`, max `2 MiB`).
- **Units & Rules:** `EPSG:4326`, dates `YYYY-MM-DD`, missing values as empty/`null` (never `-99.9` or `0`), `rainfall_mm` (`mm/day`), `temp_c` (`°C`), `area_ha` (`ha`).
- **Valid CSV Example:**
  ```csv
  parcel_id,season_year,crop,sowing_date,area_ha,latitude,longitude,rainfall_mm,temp_c
  P1,2025,maize,2025-05-15,1.5,14.635,-90.513,12.4,24.1
  ```
- **Valid GeoJSON Example (Polygon/MultiPolygon in `EPSG:4326`):**
  ```json
  {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "properties": {
          "parcel_id": "P1",
          "season_year": 2025,
          "crop": "maize",
          "sowing_date": "2025-05-15",
          "area_ha": 1.5
        },
        "geometry": {
          "type": "Polygon",
          "coordinates": [
            [
              [-90.515, 14.633],
              [-90.511, 14.633],
              [-90.511, 14.637],
              [-90.515, 14.637],
              [-90.515, 14.633]
            ]
          ]
        }
      }
    ]
  }
  ```
- **Response (`201 Created`):** Shows `status` (`"accepted"` or `"rejected"`), `rows_total`, `rows_accepted`, and row-level `errors` (`[{ row, column, message }]`).

### 6. Climate Context: ENSO Series — `GET /v1/climate/enso`
- **Suggested Screen:** Climate Timeline Panel.
- **Fields & Units:** `threshold_c` (`0.5 °C`), `items[]` (`month` `YYYY-MM`, `oni` `°C`, `roni` `°C`, `phase`: `"el_nino" | "la_nina" | "neutral"`), `source`, and **`disclaimer`**.
- **Snapshot Example:** [`examples/enso.json`](examples/enso.json).

### 7. Climate Context: NASA POWER Monthly Series — `GET /v1/climate/nasa-power?start=2025-01&end=2025-12`
- **Suggested Screen:** Climate Context Chart (explicitly label as ~50 km reanalysis grid cell at `14.59, -90.53`, not a weather station).
- **Units:** `rainfall_mm` (`mm/month`), `temperature_mean_c` / `temperature_min_c` / `temperature_max_c` (`°C`), `relative_humidity_pct` (`%`), `solar_radiation_mj_m2` (`MJ/m²/day`), `wind_speed_kmh` (`km/h`). Missing values are `null`.
- **Snapshot Example:** [`examples/nasa_power.json`](examples/nasa_power.json).

### 8. Scenario Simulation — `POST /v1/scenarios/simulate`
- **Suggested Screen:** What-If Scenario Simulator (`rainfall_change_pct` in `[-80, 100]`, `temperature_change_c` in `[-5, 8]`, `enso_phase`).
- **Request:**
  ```json
  {
    "farm_id": "22222222-2222-4222-8222-222222222222",
    "crop": "maize",
    "scenario": {
      "rainfall_change_pct": -15,
      "temperature_change_c": 1.2,
      "enso_phase": "el_nino"
    }
  }
  ```
- **Response (`200 OK`):** `baseline` & `scenario` (`p10`, `p50`, `p90` in `%` yield anomaly), `attributions`, `out_of_range_inputs`, `provenance` (`model_version`, `data_versions`), and **`disclaimer`**. See [`examples/simulate.json`](examples/simulate.json).

### 9. Compare Rotation Strategies (>= 3) — `POST /v1/farms/{farm_id}/recommendations`
- **Suggested Screen:** Rotation Comparison Cards & Detail Drawer.
- **Request:**
  ```json
  {
    "scenario": {
      "rainfall_change_pct": -15,
      "temperature_change_c": 1.2,
      "enso_phase": "el_nino"
    }
  }
  ```
- **Response (`201 Created`):** Always returns `>= 3` strategies (at least one with `is_current: true`), `overall_score` (`0..1`), 7 `scores` (`0..1`), `uncertainty` (`low`, `high`), the 5 required blocks (`why`, `evidence`, `benefits`, `gaps`, `risks`), `needs_local_review` (`true`), `provenance` (`model_name`, `model_version`, `data_versions`, `input_hash`, `generated_at`), and **`disclaimer`**.
- **Snapshot Example:** [`examples/recommendations.json`](examples/recommendations.json).
