"""Realistic Guatemala stub payloads anchored at the INSIVUMEH reference point."""

from typing import Any

DISCLAIMER_TEXT = (
    "Decision support only: these predictions and crop rotation comparisons carry "
    "uncertainty and do not replace the judgment of farmers or local agronomists. "
    "INSIVUMEH station observations are preliminary point measurements in Guatemala City."
)

STUB_PROVENANCE: dict[str, Any] = {
    "model_name": "lightgbm-guatemala-yield-anomaly",
    "model_version": "0.1.0-stub",
    "data_versions": [
        {
            "dataset_id": "climate_insivumeh_daily",
            "version": "2025.1",
            "source": "INSIVUMEH Guatemala City Station",
            "date_range": "1995-01-01/2025-12-31",
            "spatial_resolution": "point (14.5869, -90.5328)",
            "is_preliminary": True,
        },
        {
            "dataset_id": "chirps_v3_rainfall",
            "version": "3.0.2025",
            "source": "UCSB CHG CHIRPS v3",
            "date_range": "1981-01-01/2025-10-31",
            "spatial_resolution": "0.05 deg (~5.5 km)",
            "is_preliminary": False,
        },
        {
            "dataset_id": "noaa_cpc_enso",
            "version": "2025.10",
            "source": "NOAA Climate Prediction Center (ONI & RONI)",
            "date_range": "1950-01/2025-10",
            "spatial_resolution": "global index",
            "is_preliminary": False,
        },
        {
            "dataset_id": "soilgrids_v2",
            "version": "2.0",
            "source": "ISRIC SoilGrids 2.0",
            "date_range": "static",
            "spatial_resolution": "250 m",
            "is_preliminary": False,
        },
    ],
    "input_hash": "sha256:8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
    "generated_at": "2025-11-14T12:00:00Z",
}

STUB_USER: dict[str, Any] = {
    "id": "usr_gt_001",
    "email": "farmer@example.gt",
    "full_name": "Maria Ixchel",
    "role": "farmer",
    "created_at": "2025-11-01T08:30:00Z",
}

STUB_FARMS: list[dict[str, Any]] = [
    {
        "id": "farm_insivumeh_001",
        "name": "Finca Experimental INSIVUMEH",
        "department": "Guatemala",
        "municipality": "Guatemala City",
        "reference_point": {
            "latitude": 14.5869,
            "longitude": -90.5328,
        },
        "polygon": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-90.5340, 14.5860],
                    [-90.5315, 14.5860],
                    [-90.5315, 14.5880],
                    [-90.5340, 14.5880],
                    [-90.5340, 14.5860],
                ]
            ],
        },
        "area_ha": 4.8,
        "elevation_m": 1502.0,
        "current_rotation": ["maize"],
        "station_reference": "INSIVUMEH Central (Zone 13, Guatemala City)",
        "created_at": "2025-11-01T09:00:00Z",
        "updated_at": "2025-11-10T15:20:00Z",
    },
    {
        "id": "farm_sacatepequez_002",
        "name": "Parcela Los Volcanes",
        "department": "Sacatepequez",
        "municipality": "San Lucas Sacatepequez",
        "reference_point": {
            "latitude": 14.6111,
            "longitude": -90.6569,
        },
        "polygon": None,
        "area_ha": 2.4,
        "elevation_m": 2060.0,
        "current_rotation": ["maize", "black_bean"],
        "station_reference": "INSIVUMEH Central + CHIRPS 0.05 deg cell",
        "created_at": "2025-11-03T11:15:00Z",
        "updated_at": "2025-11-11T10:00:00Z",
    },
]

STUB_UPLOADS: list[dict[str, Any]] = [
    {
        "id": "upl_gt_001",
        "farm_id": "farm_insivumeh_001",
        "filename": "insivumeh_parcel_yields_2021_2024.csv",
        "format": "csv",
        "status": "validated_with_errors",
        "total_rows": 12,
        "valid_rows": 11,
        "row_errors": [
            {
                "row": 7,
                "column": "rainfall_mm",
                "code": "sentinel_value_rejected",
                "message": "Sentinel value -99.9 is not allowed; use empty cell for missing data.",
            }
        ],
        "created_at": "2025-11-12T14:00:00Z",
    }
]

STUB_PRIORITIES: dict[str, Any] = {
    "farm_id": "farm_insivumeh_001",
    "weights": {
        "yield_stability": 0.35,
        "soil_health": 0.25,
        "water_efficiency": 0.20,
        "income_diversification": 0.10,
        "low_input_cost": 0.10,
    },
    "irrigation_available": False,
    "max_fallow_days": 60,
    "excluded_crops": [],
    "notes": (
        "Rainfed hillside parcel; prioritize ground cover during May and September heavy rains."
    ),
    "updated_at": "2025-11-12T16:30:00Z",
}

STUB_INSIGHTS: dict[str, Any] = {
    "farm_id": "farm_insivumeh_001",
    "bare_field_periods": [
        {
            "start_date": "2025-01-15",
            "end_date": "2025-04-25",
            "duration_days": 100,
            "mean_ndvi": 0.21,
            "erosion_exposure": "high",
            "explanation": (
                "Low vegetation vigor (MODIS/Sentinel-2 NDVI < 0.25) prior to onset of May rains "
                "leaves topsoil exposed to first intense convective storms."
            ),
        }
    ],
    "vulnerable_seasons": [
        {
            "season_name": "Mid-summer drought (Canicula)",
            "months": "July-August",
            "primary_hazard": "dry_spell_canicula",
            "enso_sensitivity": (
                "El Nino events typically prolong dry spells during July and August in the "
                "Guatemalan Dry Corridor and Central Highlands, stressing maize at flowering."
            ),
            "recommended_watch": "Monitor 10-day water balance and root-zone soil moisture (SMAP).",
        },
        {
            "season_name": "Late rainy season peak",
            "months": "September-October",
            "primary_hazard": "extreme_rainfall",
            "enso_sensitivity": (
                "La Nina increases the frequency of daily rainfall events >= 50 mm "
                "(INSIVUMEH historical max 232.5 mm/day), raising waterlogging and bean "
                "disease risk."
            ),
            "recommended_watch": "Ensure contour drainage and avoid bare soil on slopes > 8%.",
        },
    ],
    "provenance": STUB_PROVENANCE,
    "disclaimer": DISCLAIMER_TEXT,
}

STUB_LAYERS: list[dict[str, Any]] = [
    {
        "id": "chirps_rainfall_anomaly",
        "name": "Rainfall Anomaly (CHIRPS v3)",
        "category": "climate",
        "description": (
            "Monthly rainfall anomaly in percent relative to 1991-2020 climatology (~1,280 mm/year "
            "at INSIVUMEH Guatemala City, 93% between May and October)."
        ),
        "tile_url_template": "https://tiles.example.gt/clean/chirps_v3/{z}/{x}/{y}.png",
        "legend": {
            "unit": "%",
            "palette_name": "BrBG-colorblind-safe",
            "color_blind_safe": True,
            "stops": [
                {"value": -50.0, "color": "#8c510a", "label": "-50% (severe deficit)"},
                {"value": 0.0, "color": "#f5f5f5", "label": "0% (normal)"},
                {"value": 50.0, "color": "#01665e", "label": "+50% (surplus)"},
            ],
        },
        "source": {
            "provider": "UCSB Climate Hazards Center",
            "dataset_id": "chirps_v3_rainfall",
            "version": "3.0.2025",
            "spatial_resolution": "0.05 deg (~5.5 km)",
            "date_range": "1981-01-01/2025-10-31",
            "measurement_type": "satellite_derived",
            "limitation_note": (
                "Daily CHIRPS values are disaggregated from pentads; compare with INSIVUMEH "
                "ground station and GPM IMERG for single-day extremes."
            ),
        },
    },
    {
        "id": "modis_ndvi_16d",
        "name": "Vegetation Vigor NDVI (MODIS MOD13Q1)",
        "category": "vegetation",
        "description": (
            "16-day composite Normalized Difference Vegetation Index at 250 m resolution."
        ),
        "tile_url_template": "https://tiles.example.gt/clean/modis_ndvi/{z}/{x}/{y}.png",
        "legend": {
            "unit": "NDVI",
            "palette_name": "YlGnBu-colorblind-safe",
            "color_blind_safe": True,
            "stops": [
                {"value": 0.15, "color": "#ffffcc", "label": "0.15 (bare soil)"},
                {"value": 0.50, "color": "#41b6c4", "label": "0.50 (moderate cover)"},
                {"value": 0.85, "color": "#0c2c84", "label": "0.85 (dense canopy)"},
            ],
        },
        "source": {
            "provider": "NASA LP DAAC / Microsoft Planetary Computer",
            "dataset_id": "modis-13Q1-061",
            "version": "061",
            "spatial_resolution": "250 m",
            "date_range": "2000-02-18/2025-10-31",
            "measurement_type": "satellite_derived",
            "limitation_note": (
                "Cloud cover during the May-October rainy season in Guatemala can reduce valid "
                "optical passes."
            ),
        },
    },
    {
        "id": "soilgrids_soc_0_30cm",
        "name": "Soil Organic Carbon 0-30 cm (SoilGrids 2.0)",
        "category": "soil",
        "description": "Predicted soil organic carbon stock in the top 30 cm.",
        "tile_url_template": "https://tiles.example.gt/clean/soilgrids_soc/{z}/{x}/{y}.png",
        "legend": {
            "unit": "g/kg",
            "palette_name": "Viridis-colorblind-safe",
            "color_blind_safe": True,
            "stops": [
                {"value": 10.0, "color": "#440154", "label": "10 g/kg (low)"},
                {"value": 30.0, "color": "#21918c", "label": "30 g/kg (medium)"},
                {"value": 60.0, "color": "#fde725", "label": "60 g/kg (high)"},
            ],
        },
        "source": {
            "provider": "ISRIC World Soil Information",
            "dataset_id": "soilgrids_v2",
            "version": "2.0",
            "spatial_resolution": "250 m",
            "date_range": "static",
            "measurement_type": "soil_prediction",
            "limitation_note": (
                "250 m machine-learning soil prediction, not a laboratory soil analysis. "
                "A local soil test on the farm always overrides this layer."
            ),
        },
    },
]

STUB_ENSO_SERIES: list[dict[str, Any]] = [
    {
        "month": "2023-11",
        "oni_c": 1.9,
        "roni_c": 1.7,
        "phase": "el_nino",
        "rainfall_anomaly_note": "Strong El Nino; delayed rainy onset and extended canicula risk.",
    },
    {
        "month": "2024-05",
        "oni_c": 0.2,
        "roni_c": 0.1,
        "phase": "neutral",
        "rainfall_anomaly_note": "ENSO neutral transition at the start of the Primera season.",
    },
    {
        "month": "2024-10",
        "oni_c": -0.6,
        "roni_c": -0.7,
        "phase": "la_nina",
        "rainfall_anomaly_note": (
            "La Nina conditions; elevated Postrera rainfall in Central Highlands."
        ),
    },
    {
        "month": "2025-05",
        "oni_c": -0.5,
        "roni_c": -0.6,
        "phase": "la_nina",
        "rainfall_anomaly_note": "Early Primera rainfall above average near Guatemala City.",
    },
]

STUB_SIMULATION: dict[str, Any] = {
    "farm_id": "farm_insivumeh_001",
    "crop_id": "maize",
    "metric_name": "projected_grain_yield",
    "baseline": {
        "p10": 2450.0,
        "p50": 3100.0,
        "p90": 3650.0,
        "unit": "kg/ha",
        "confidence_note": "10th-90th percentile interval from whole-year cross-validation.",
    },
    "scenario": {
        "p10": 1950.0,
        "p50": 2680.0,
        "p90": 3290.0,
        "unit": "kg/ha",
        "confidence_note": "Wider lower tail due to simulated mid-season moisture deficit.",
    },
    "out_of_training_range": False,
    "range_warning": None,
    "top_attributions": [
        {
            "feature": "july_august_rainfall_anomaly_pct",
            "shap_value": -240.5,
            "direction": "negative",
            "explanation": (
                "Simulated rainfall reduction during flowering (Canicula) lowers median yield."
            ),
        },
        {
            "feature": "enso_oni_lag_3m",
            "shap_value": -115.0,
            "direction": "negative",
            "explanation": "Warm ENSO phase lags correlate with drier July-August conditions.",
        },
        {
            "feature": "root_zone_soil_moisture_may",
            "shap_value": 85.2,
            "direction": "positive",
            "explanation": "Adequate May establishment moisture buffers early vegetative growth.",
        },
    ],
    "timeline": [
        {
            "period": "2025-05",
            "baseline_p50": 520.0,
            "scenario_p10": 410.0,
            "scenario_p50": 480.0,
            "scenario_p90": 560.0,
            "water_balance_mm": 42.0,
        },
        {
            "period": "2025-07",
            "baseline_p50": 1850.0,
            "scenario_p10": 1320.0,
            "scenario_p50": 1590.0,
            "scenario_p90": 1910.0,
            "water_balance_mm": -18.5,
        },
        {
            "period": "2025-10",
            "baseline_p50": 3100.0,
            "scenario_p10": 1950.0,
            "scenario_p50": 2680.0,
            "scenario_p90": 3290.0,
            "water_balance_mm": 65.0,
        },
    ],
    "provenance": STUB_PROVENANCE,
    "disclaimer": DISCLAIMER_TEXT,
}

STUB_RECOMMENDATION: dict[str, Any] = {
    "id": "rec_gt_001",
    "farm_id": "farm_insivumeh_001",
    "scenario_summary": (
        "Comparison for Guatemala City highlands (1,502 m, ~1,280 mm annual rain, "
        "93% May-October) under neutral-to-La Nina transition."
    ),
    "strategies": [
        {
            "id": "strat_current_monocrop_maize",
            "name": "Current Rotation: Continuous Rainfed Maize + Dry-Season Fallow",
            "is_current_rotation": True,
            "sequence": ["maize (May-Oct)", "bare fallow (Nov-Apr)"],
            "why": [
                "Included as the baseline rotation currently practiced on the parcel.",
                "Matches local staple grain familiarity and established seed supply.",
            ],
            "evidence": [
                (
                    "INSIVUMEH 1995-2025 series shows 93% of annual rainfall (1,280 mm) "
                    "falls May-October."
                ),
                (
                    "MODIS NDVI history indicates 100+ days of low ground cover (<0.25) "
                    "during Nov-Apr fallow."
                ),
            ],
            "benefits": [
                "Single-crop management with familiar sowing dates at the onset of May rains.",
                "No additional seed cost for relay or cover crops.",
            ],
            "gaps": [
                "No parcel-level laboratory soil nitrogen or pH analysis has been uploaded.",
                (
                    "Local incidence of fall armyworm (Spodoptera frugiperda) and ear rot "
                    "is unrecorded."
                ),
            ],
            "risks": [
                "High vulnerability to July-August Canicula dry spells during silking.",
                (
                    "Bare soil from January to April exposes slopes to erosion when heavy "
                    "May storms arrive."
                ),
                "Continuous cereal monocropping depletes soil nitrogen and organic matter.",
            ],
            "needs_local_review": True,
            "uncertainty": {
                "p10": 2100.0,
                "p50": 2950.0,
                "p90": 3550.0,
                "unit": "kg/ha maize equivalent",
                "confidence_note": (
                    "Wide downside tail in years with prolonged Canicula or excess October rain."
                ),
            },
            "scores": {
                "overall": 58.0,
                "yield_stability": 55.0,
                "soil_health": 42.0,
                "water_efficiency": 54.0,
                "income_diversification": 40.0,
                "low_input_cost": 82.0,
            },
        },
        {
            "id": "strat_maize_black_bean_relay",
            "name": "Maize (Primera) + Bush Black Bean Relay (Postrera) + Mulch Retention",
            "is_current_rotation": False,
            "sequence": [
                "maize (May-Sep)",
                "black_bean relay (Aug-Nov)",
                "crop residue mulch (Dec-Apr)",
            ],
            "why": [
                "Aligns with farmer priorities for yield stability (0.35) and soil health (0.25).",
                "Takes advantage of bimodal rainy peaks while fixing atmospheric nitrogen.",
            ],
            "evidence": [
                (
                    "FAO ECOCROP and GAEZ v5 show high suitability for Phaseolus vulgaris "
                    "at 1,500 m elevation."
                ),
                (
                    "INSIVUMEH August-October rainfall supports short-cycle (75-85 day) "
                    "Postrera beans."
                ),
            ],
            "benefits": [
                (
                    "Symbiotic nitrogen fixation reduces synthetic fertilizer demand for the "
                    "next maize cycle."
                ),
                (
                    "Living canopy in August-November protects soil during peak "
                    "September-October rainfall."
                ),
                (
                    "Provides two harvestable staple crops (maize and black bean) in a "
                    "single rainy season."
                ),
            ],
            "gaps": [
                (
                    "Exact field drainage capacity and slope gradient at sub-parcel scale "
                    "are not verified."
                ),
                (
                    "Availability of disease-tolerant local black bean varieties "
                    "(e.g., ICTA Ligero) must be checked."
                ),
            ],
            "risks": [
                (
                    "Under strong La Nina years (>50 mm/day rain events in September-October), "
                    "black beans face fungal web blight and root rot risk."
                ),
                (
                    "Requires timely labor in August to establish relay rows without damaging "
                    "standing maize."
                ),
            ],
            "needs_local_review": True,
            "uncertainty": {
                "p10": 2650.0,
                "p50": 3420.0,
                "p90": 4050.0,
                "unit": "kg/ha maize-equivalent system output",
                "confidence_note": (
                    "Higher median and 10th percentile due to risk spreading across two "
                    "crop cycles."
                ),
            },
            "scores": {
                "overall": 82.0,
                "yield_stability": 84.0,
                "soil_health": 83.0,
                "water_efficiency": 80.0,
                "income_diversification": 85.0,
                "low_input_cost": 74.0,
            },
        },
        {
            "id": "strat_maize_fava_canavalia_cover",
            "name": "Maize-Legume Intercrop + Drought-Tolerant Green Manure Cover (Canavalia)",
            "is_current_rotation": False,
            "sequence": [
                "maize + climbing bean intercrop (May-Oct)",
                "canavalia ensiformis cover crop (Oct-Mar)",
            ],
            "why": [
                (
                    "Maximizes soil organic carbon restoration and eliminates the dry-season "
                    "bare-field window."
                ),
                (
                    "Deep-rooted Canavalia utilizes residual October soil moisture through "
                    "the dry season."
                ),
            ],
            "evidence": [
                (
                    "MODIS/Sentinel-2 bare-field analysis flags Jan-Apr as the main soil "
                    "exposure period."
                ),
                (
                    "FAO-56 crop water balance indicates residual root-zone moisture in "
                    "November is sufficient to establish Canavalia."
                ),
            ],
            "benefits": [
                (
                    "High biomass cover suppresses weeds and buffers soil temperature during "
                    "the dry season (Nov-Apr <40 mm/month)."
                ),
                (
                    "Substantially reduces runoff and topsoil loss during early May "
                    "convective storms."
                ),
            ],
            "gaps": [
                (
                    "Local seed availability and cost for Canavalia ensiformis or Mucuna "
                    "are not in the dataset."
                ),
                (
                    "Soil phosphorus levels (which limit legume nodulation in volcanic ash "
                    "soils) are unknown."
                ),
            ],
            "risks": [
                (
                    "Cover crop produces no direct cash harvest in the dry season, requiring "
                    "upfront seed and slashing labor."
                ),
                (
                    "Climbing beans can increase maize lodging if high wind events "
                    "(INSIVUMEH max 60.7 km/h) occur in September."
                ),
            ],
            "needs_local_review": True,
            "uncertainty": {
                "p10": 2500.0,
                "p50": 3280.0,
                "p90": 3920.0,
                "unit": "kg/ha maize-equivalent system output",
                "confidence_note": (
                    "Soil moisture conservation benefits compound in year 2+ after cover "
                    "crop incorporation."
                ),
            },
            "scores": {
                "overall": 77.0,
                "yield_stability": 79.0,
                "soil_health": 92.0,
                "water_efficiency": 85.0,
                "income_diversification": 64.0,
                "low_input_cost": 62.0,
            },
        },
    ],
    "provenance": STUB_PROVENANCE,
    "disclaimer": DISCLAIMER_TEXT,
}

STUB_SEARCH_CATALOG: list[dict[str, Any]] = [
    {
        "id": "crop_maize",
        "type": "crop",
        "name": "Maize (Zea mays)",
        "aliases": ["maiz", "corn", "milpa", "elote"],
        "similarity": 0.92,
        "summary": "Primary staple cereal in Guatemala; rainfed Primera sowing in May.",
    },
    {
        "id": "crop_black_bean",
        "type": "crop",
        "name": "Black Bean (Phaseolus vulgaris)",
        "aliases": ["frijol", "frijol negro", "ejote"],
        "similarity": 0.85,
        "summary": "Nitrogen-fixing legume grown in relay (Postrera) or intercropped with maize.",
    },
    {
        "id": "crop_coffee_arabica",
        "type": "crop",
        "name": "Arabica Coffee (Coffea arabica)",
        "aliases": ["cafe", "cafe arabigo"],
        "similarity": 0.78,
        "summary": "Perennial shade-grown highland crop suited to 1,200-1,800 m elevation.",
    },
    {
        "id": "place_guatemala_insivumeh",
        "type": "place",
        "name": "Guatemala City (INSIVUMEH Station)",
        "aliases": ["ciudad de guatemala", "insivumeh", "zona 13"],
        "similarity": 0.90,
        "summary": "Pilot reference point (14.5869, -90.5328) at 1,502 m elevation.",
    },
    {
        "id": "place_antigua_sacatepequez",
        "type": "place",
        "name": "Antigua Guatemala, Sacatepequez",
        "aliases": ["antigua", "sacatepequez"],
        "similarity": 0.81,
        "summary": "Central Highlands agricultural municipality west of Guatemala City.",
    },
    {
        "id": "farm_insivumeh_001",
        "type": "farm",
        "name": "Finca Experimental INSIVUMEH",
        "aliases": ["finca insivumeh", "experimental"],
        "similarity": 0.88,
        "summary": "4.8 ha reference farm in Guatemala City.",
    },
]
