#!/usr/bin/env bash
set -euo pipefail

GITHUB_ORG="${GITHUB_ORG:-Quetzpaciales-Space-Apps-Team}"
REPOS=(
  "agrofarm-docs"
  "agrofarm-api"
  "agrofarm-analytic"
  "agrofarm-frontend"
)
BRANCHES=(
  "develop"
  "main"
)

for repo in "${REPOS[@]}"; do
  echo "Setting default branch to 'develop' on ${GITHUB_ORG}/${repo}..."
  gh api \
    --method PATCH \
    -H "Accept: application/vnd.github+json" \
    "/repos/${GITHUB_ORG}/${repo}" \
    -f default_branch="develop" >/dev/null

  for branch in "${BRANCHES[@]}"; do
    echo "Protecting ${GITHUB_ORG}/${repo}:${branch} (requiring PR and ci-gate)..."
    gh api \
      --method PUT \
      -H "Accept: application/vnd.github+json" \
      "/repos/${GITHUB_ORG}/${repo}/branches/${branch}/protection" \
      --input - <<'EOF' >/dev/null
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["ci-gate"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_linear_history": false,
  "required_conversation_resolution": true
}
EOF
  done
done

echo "Branch protection rules applied across all four AgroFarm repositories."
