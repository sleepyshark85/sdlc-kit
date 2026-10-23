#!/usr/bin/env bash
# Applies the repository settings the SDLC relies on. The owner runs it once after creating the repository, and again
# when a language pack adds required checks; agents are blocked from changing these settings (the plugin's git hook).
#
# Usage: scripts/setup-repo.sh <owner/repo> <reviewer login> [extra required check...]
#   The reviewer login is the GitHub identity the reviewer agent posts its verdicts as (docs/conventions.md, The
#   review gate); the owner's own login is trusted as well. Extra checks are a pack's, such as "dotnet-ubuntu".
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 <owner/repo> <reviewer login> [extra required check...]" >&2
  exit 64
fi
repo=$1
reviewer=$2
shift 2
owner_login=$(gh api user --jq .login)
checks=(review quality "codeql (actions)" "$@")

echo "Merge commits only, auto-merge on: the pipeline merges with 'gh pr merge --auto --merge'."
gh api -X PATCH "repos/$repo" \
  -F allow_merge_commit=true -F allow_squash_merge=false -F allow_rebase_merge=false \
  -F allow_auto_merge=true -F delete_branch_on_merge=false > /dev/null

echo "Branch protection on main: required checks, up to date, resolved conversations, admins included."
contexts=$(printf '%s\n' "${checks[@]}" | python3 -c 'import json, sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')
gh api -X PUT "repos/$repo/branches/main/protection" --input - > /dev/null <<EOF
{
  "required_status_checks": {"strict": true, "contexts": $contexts},
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "required_conversation_resolution": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

echo "Verdicts count only from the reviewer's identity and the owner's."
gh variable set REVIEWERS --repo "$repo" --body "$reviewer,$owner_login"

echo "Secret scanning, push protection, non-provider patterns and validity checks; Dependabot security updates."
# A private repository needs GitHub's secret protection for these; without it GitHub refuses, and the script says so.
if ! gh api -X PATCH "repos/$repo" --input - > /dev/null <<'EOF'
{"security_and_analysis": {
  "secret_scanning": {"status": "enabled"},
  "secret_scanning_push_protection": {"status": "enabled"},
  "secret_scanning_non_provider_patterns": {"status": "enabled"},
  "secret_scanning_validity_checks": {"status": "enabled"}}}
EOF
then
  echo "warning: secret scanning could not be enabled (a private repository needs GitHub's secret protection)." >&2
fi
gh api -X PUT "repos/$repo/vulnerability-alerts" > /dev/null
gh api -X PUT "repos/$repo/automated-security-fixes" > /dev/null

echo "Done. Required checks: ${checks[*]}"
