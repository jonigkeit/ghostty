#!/usr/bin/env bash
# Run in a clean checkout of the integration branch. Push only after both merges.
set -euo pipefail

branch=feat/quickterm-with-tab
if [[ $(git branch --show-current) != "$branch" ]]; then
  echo "Expected a checkout of $branch" >&2
  exit 1
fi
if [[ -n $(git status --porcelain) ]]; then
  echo "Refusing to synchronize a dirty checkout" >&2
  exit 1
fi

before=$(git rev-parse HEAD)
git fetch --no-tags origin "$branch"
if [[ $(git rev-parse FETCH_HEAD) != "$before" ]]; then
  echo "Checkout is stale; retry from origin/$branch" >&2
  exit 1
fi
git fetch --no-tags ghostty main
git fetch --no-tags adrum feat/quickterm-with-tab

for source in ghostty/main adrum/feat/quickterm-with-tab; do
  if git merge-base --is-ancestor "$source" HEAD; then
    continue
  fi
  if ! git merge --no-ff --no-edit -m "Merge $source into $branch" "$source"; then
    git merge --abort
    echo "Conflict integrating $source. Nothing has been pushed; resolve manually." >&2
    exit 1
  fi
done

after=$(git rev-parse HEAD)
changed=false
if [[ "$before" != "$after" ]]; then
  # A concurrent push is rejected instead of being overwritten.
  git push origin "HEAD:refs/heads/$branch"
  changed=true
fi
if [[ -n ${GITHUB_OUTPUT:-} ]]; then
  printf 'changed=%s\nsha=%s\n' "$changed" "$after" >> "$GITHUB_OUTPUT"
fi
printf 'changed=%s\nsha=%s\n' "$changed" "$after"
