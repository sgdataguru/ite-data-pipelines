#!/usr/bin/env bash
# Bring the latest workshop files into YOUR copy of the repository.
#
# Why this exists: your repository was created with "Use this template", so
# "git pull" only pulls from your own copy on GitHub. It never sees the new
# files the facilitators add to sgdataguru/ite-data-pipelines.
#
# Run from anywhere inside your repository:
#     make update
# or, the first time (before your Makefile has the "update" target):
#     curl -fsSL https://raw.githubusercontent.com/sgdataguru/ite-data-pipelines/main/scripts/update_from_template.sh | bash
#
# What it does:
#   1. Adds a remote called "template" (the facilitators' repository) and fetches it.
#   2. ALWAYS overwrites the facilitator-owned files listed below.
#   3. Adds your starter files ONLY IF you do not have them yet.
#   4. Never overwrites your own work: dbt/models/, dbt/tests/, dbt/dbt_project.yml,
#      dbt/profiles.yml, lab1/starter, lab2/starter, journal.md, .devcontainer/.
#   5. Makes every new terminal load scripts/workshop_env.sh (via ~/.bashrc),
#      so dbt and DuckDB find the right paths without rebuilding the Codespace.
# Nothing is committed. You review the changes, then commit them yourself.

set -euo pipefail

TEMPLATE_URL="https://github.com/sgdataguru/ite-data-pipelines.git"
TEMPLATE_REF="template/main"

# Facilitator-owned: always replaced with the template's version.
ALWAYS_UPDATE=(
  Makefile
  .gitignore
  requirements.txt
  requirements-airflow.txt
  ruff.toml
  scripts
  mock_api
  data
  dbt/reference
  dbt/macros
  dbt/seeds
  enrich
  day1
  day2
  day3
  templates
  tests
  .github
  dags/reference_pipeline.py
  dags/pipeline_alerts.py
  README.md
  lab1/INSTRUCTIONS.md
  lab2/INSTRUCTIONS.md
  # Solutions are held back from the template until the facilitator
  # releases them after each lab; then "make update" brings them in.
  lab1/solution
  lab2/solution
)

# Participant-owned starter files: added once, never overwritten.
# (Copies made from the Day 1 template have no dbt project at all.)
ADD_IF_MISSING=(
  dags/capstone_pipeline.py
  dbt/dbt_project.yml
  dbt/profiles.yml
  dbt/models/sources.yml
  dbt/models/silver/README.md
  dbt/models/gold/README.md
  dbt/tests/README.md
)

# Work from the repository root, wherever the command was typed.
if ! ROOT=$(git rev-parse --show-toplevel 2>/dev/null); then
  echo "This is not a Git repository. cd into your ite-data-pipelines folder and try again."
  exit 1
fi
cd "$ROOT"

# 1. Make sure the "template" remote exists, then fetch it.
if ! git remote get-url template >/dev/null 2>&1; then
  git remote add template "$TEMPLATE_URL"
  echo "Added remote 'template' -> $TEMPLATE_URL"
fi
echo "Fetching the latest workshop files..."
git fetch --quiet template

# True if <path> exists in the template's main branch.
in_template() {
  git cat-file -e "$TEMPLATE_REF:$1" 2>/dev/null
}

# 2. Facilitator-owned paths: take the template's version.
for path in "${ALWAYS_UPDATE[@]}"; do
  if ! in_template "$path"; then
    continue                      # not in the template yet: skip quietly
  fi
  git checkout "$TEMPLATE_REF" -- "$path"
  echo "Updated  $path"
done

# 3. Starter files: add only if missing, so your edits are never lost.
for path in "${ADD_IF_MISSING[@]}"; do
  if ! in_template "$path"; then
    continue
  fi
  if [ -e "$path" ]; then
    echo "Kept     $path (yours already exists)"
  else
    git checkout "$TEMPLATE_REF" -- "$path"
    echo "Added    $path"
  fi
done

# 4. Make every new terminal load the workshop environment variables.
BASHRC="$HOME/.bashrc"
HOOK="[ -f \"$ROOT/scripts/workshop_env.sh\" ] && source \"$ROOT/scripts/workshop_env.sh\"  # ite-data-pipelines"
if [ -f "$ROOT/scripts/workshop_env.sh" ] && ! grep -qs "# ite-data-pipelines" "$BASHRC"; then
  echo "$HOOK" >> "$BASHRC"
  echo "Added    workshop settings to ~/.bashrc (new terminals get them automatically)"
fi

echo
echo "For THIS terminal, run once:  source scripts/workshop_env.sh"
echo 'Done. Review with git status, then commit: git commit -am "Sync workshop files"'
