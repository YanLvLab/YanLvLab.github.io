#!/usr/bin/env bash
# Daily publish: merge prepared inbox files with update.py, then commit + push only if something changed.
# Token: $GITHUB_TOKEN if set and valid, otherwise ~/.secrets/github_token (outside the repo, mode 600).
# It is only held in memory for this run; never printed, never written to a file or the remote URL.
#
#   scripts/publish.sh                       # merge inbox/<today>-*.json (Shanghai date), then publish
#   scripts/publish.sh --no-update           # just publish whatever is already changed
#   scripts/publish.sh -- <update.py args>   # custom update.py arguments
set -euo pipefail
cd "$(dirname "$0")/.."

REPO_URL="https://github.com/YanLvLab/YanLvLab.github.io.git"
BRANCH="main"
TODAY="$(TZ=Asia/Shanghai date +%Y%m%d)"

if [[ "${1:-}" == "--no-update" ]]; then
  :
elif [[ "${1:-}" == "--" ]]; then
  shift; python3 scripts/update.py "$@"
else
  shopt -s nullglob
  files=(inbox/"$TODAY"-*posts*.json inbox/"$TODAY"-*replies*.json inbox/"$TODAY"-*full*.json)
  prof=(inbox/"$TODAY"-profile.json)
  if (( ${#files[@]} )); then
    args=(--input "${files[@]}")
    (( ${#prof[@]} )) && args+=(--profile "${prof[0]}")
    python3 scripts/update.py "${args[@]}"
  else
    echo "no inbox files for $TODAY; skipping update.py"
  fi
fi

# guard: private folders must stay ignored
for d in raw/ review/ inbox/; do
  git check-ignore -q "$d" || { echo "refusing to publish: $d is not in .gitignore" >&2; exit 1; }
done

token_ok() {  # 200 from /user means the token works; the token goes via a header file descriptor, not argv
  [[ -n "${1:-}" ]] || return 1
  [[ "$(curl -s -o /dev/null -w '%{http_code}' -H @<(printf 'Authorization: Bearer %s\n' "$1") https://api.github.com/user)" == 200 ]]
}
resolve_token() {
  if token_ok "${GITHUB_TOKEN:-}"; then return 0; fi
  local f="${GITHUB_TOKEN_FILE:-$HOME/.secrets/github_token}"
  if [[ -r "$f" ]]; then
    GITHUB_TOKEN="$(tr -d '[:space:]' < "$f")"; export GITHUB_TOKEN
    token_ok "$GITHUB_TOKEN" && return 0
  fi
  echo "no valid GitHub token (env GITHUB_TOKEN or $f)" >&2; exit 1
}

git add -A
if git diff --cached --quiet; then
  local_head="$(git rev-parse HEAD 2>/dev/null || true)"
  resolve_token
  remote_head="$(git -c credential.helper= -c 'credential.helper=!f() { echo username=x-access-token; echo "password=${GITHUB_TOKEN}"; }; f' \
                 ls-remote "$REPO_URL" "refs/heads/$BRANCH" 2>/dev/null | cut -f1 || true)"
  if [[ -z "$local_head" || "$local_head" == "$remote_head" ]]; then
    echo "no changes; nothing to publish"
    exit 0
  fi
  echo "no new changes, but local $BRANCH is not on GitHub yet; pushing"
else
  resolve_token
  git -c user.name="${GIT_AUTHOR_NAME:-YanLvLab}" -c user.email="${GIT_AUTHOR_EMAIL:-YanLvLab@users.noreply.github.com}" \
      commit -q -m "Daily sync $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M') (Asia/Shanghai)"
fi

# credential helper reads the token from the environment; nothing is stored
git -c credential.helper= \
    -c 'credential.helper=!f() { echo username=x-access-token; echo "password=${GITHUB_TOKEN}"; }; f' \
    push -q "$REPO_URL" "HEAD:$BRANCH"
echo "published $(git rev-parse --short HEAD)"
