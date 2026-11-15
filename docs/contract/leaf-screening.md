# Farm photo assessment contract and frontend handoff

`POST /v1/farms/{farm_id}/leaves/assess` accepts JPEG or PNG bytes, not multipart form data, JSON, base64 or a remote URL. It uses the existing bearer authentication, including a temporary demo guest for that guest's own farm. Another farmer's farm returns 404; an admin can assess an existing farm.

The browser sends the selected `File`/`Blob` as the body with `Content-Type: image/jpeg` or `image/png`, through the existing API infrastructure. Maximum input: 5 MiB. The internal classifier also enforces a decoded-pixel limit. The API forwards to `ML_SERVICE_URL/v1/leaves/assess`; Google service identity is used when `ML_AUTH=google_id_token`. The guest's bearer token is never forwarded to ML. The request ID is propagated.

Photos are held in memory for the request only. They are not saved, registered as farm observations, used for retraining or sent to a generative vision service. There is no cached diagnosis fallback. A missing model or failed service returns a problem response.

## Frontend behavior

Regenerate API types from this updated OpenAPI contract in the frontend owner's branch. Keep the existing session and request error handling. Present:

- `assessment: uncertain`: show that the model could not select a supported condition. Do not promote the highest score to a diagnosis.
- `assessment: possible_condition`: show the candidate as a possibility requiring local confirmation. Scores are uncalibrated model scores, not certainty percentages.
- Supported classes: `common_rust`, `corn_leaf_blight`, `gray_leaf_spot`, `healthy`, `insect_damage`. Generic insect damage does not identify an insect species. A healthy candidate does not rule out other conditions.
- Keep `needs_local_review`, the disclaimer, limits and guidance visible. Reference links are for local review. No pesticide product or dosage is inferred.
- Handle 400 (invalid image), 401 (session), 404 (farm unavailable), 413 (size), 415 (media type), 422 (invalid farm UUID), 502 (invalid ML response) and 503 (model/service unavailable).

The public API rejects ML output with missing class scores, nonfinite/out-of-range scores, no review requirement, an unsupported candidate, a contradictory candidate/assessment, missing model version or no limits/guidance status. It attaches an image SHA-256 input hash, generated timestamp and the standard disclaimer. It does not persist the result.

## Deployment dependency

Requires the analytic implementation of `/v1/leaves/assess` and a compatible, internally evaluated artifact configured there using `LEAF_MODEL_DIR`. This PR does not upload artifacts, change IAM or deploy services. The route may return 503 until the ML artifact is available. There are no frontend changes in this PR.
