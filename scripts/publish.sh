#!/usr/bin/env bash
# Daily publish: merge prepared inbox files with update.py, then commit + push only if something changed.
# The GitHub token is read from $GITHUB_TOKEN at run time only; it is never written to a file or the remote URL.
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

git add -A
if git diff --cached --quiet; then
  echo "no changes; nothing to publish"
  exit 0
fi

: "${GITHUB_TOKEN:?GITHUB_TOKEN is not set}"
git -c user.name="${GIT_AUTHOR_NAME:-YanLvLab}" -c user.email="${GIT_AUTHOR_EMAIL:-YanLvLab@users.noreply.github.com}" \
    commit -q -m "Daily sync $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M') (Asia/Shanghai)"

# credential helper reads the token from the environment; nothing is stored
git -c credential.helper= \
    -c 'credential.helper=!f() { echo username=x-access-token; echo "password=${GITHUB_TOKEN}"; }; f' \
    push -q "$REPO_URL" "HEAD:$BRANCH"
echo "published $(git rev-parse --short HEAD)"
