from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CD_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "cd.yml"
ROLLBACK_DOC_PATH = REPO_ROOT / "deploy" / "rollback.md"


def _load_cd_workflow() -> dict[str, Any]:
    assert CD_WORKFLOW_PATH.is_file(), "Missing .github/workflows/cd.yml"
    loaded = yaml.safe_load(CD_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_cd_workflow_triggers_on_develop_and_main_and_uses_wif_secrets() -> None:
    workflow = _load_cd_workflow()
    raw_text = CD_WORKFLOW_PATH.read_text(encoding="utf-8")

    triggers = workflow["on"]
    assert isinstance(triggers, dict)
    push_branches = triggers["push"]["branches"]
    assert "develop" in push_branches
    assert "main" in push_branches
    assert "workflow_dispatch" in triggers

    # Must use Workload Identity Federation via encrypted secrets and never hardcode identifiers
    assert "google-github-actions/auth@v2" in raw_text
    assert "secrets.GCP_WIF_PROVIDER" in raw_text
    assert "secrets.GCP_SA_CI_DEPLOYER" in raw_text
    assert "secrets.GCP_PROJECT_ID" in raw_text
    assert "credentials_json" not in raw_text
    assert ".iam.gserviceaccount.com" not in raw_text
    assert "agrofarm-spaceapps" not in raw_text


def test_cd_workflow_runs_migrations_before_deploy_and_smoke_tests_staging_and_prod() -> None:
    workflow = _load_cd_workflow()
    raw_text = CD_WORKFLOW_PATH.read_text(encoding="utf-8")
    jobs = workflow["jobs"]

    assert "deploy-staging" in jobs
    assert "deploy-production" in jobs

    staging_job = jobs["deploy-staging"]
    prod_job = jobs["deploy-production"]

    assert staging_job["environment"] == "staging"
    assert prod_job["environment"] == "production"

    # Must update and execute Cloud Run migration job before updating Cloud Run service
    assert "core-api-migrate-staging" in raw_text
    assert "gcloud run jobs execute" in raw_text
    assert "core-api-staging" in raw_text
    assert "/healthz" in raw_text
    assert "::add-mask::" in raw_text


def test_rollback_runbook_is_documented() -> None:
    assert ROLLBACK_DOC_PATH.is_file(), "Missing deploy/rollback.md"
    content = ROLLBACK_DOC_PATH.read_text(encoding="utf-8")
    assert "gcloud run services update-traffic" in content
    assert "--to-revisions" in content
    assert "core-api-migrate" in content


def test_staging_deploy_configures_live_ml_and_checks_demo_behavior() -> None:
    steps = _load_cd_workflow()["jobs"]["deploy-staging"]["steps"]
    deploy = next(
        s["run"] for s in steps if s["name"] == "Deploy new revision to Cloud Run staging"
    )
    assert "gcloud run services describe ml-service-staging" in deploy
    for setting in (
        "ML_MODE=http",
        "ML_AUTH=google_id_token",
        "DEMO_MODE=true",
        "DEMO_ML_SOURCE=live",
    ):
        assert setting in deploy
    assert "ML_SERVICE_URL=$ML_SERVICE_URL" in deploy
    assert "--update-env-vars" in deploy
    smoke = next(s["run"] for s in steps if s["name"] == "Run post-deploy smoke test")
    assert "python3 deploy/smoke_demo.py" in smoke
    assert smoke.index("/readyz") < smoke.index("python3 deploy/smoke_demo.py")
