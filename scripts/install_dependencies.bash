#!/usr/bin/env bash
# install_dependencies.sh
# Robust, resume-friendly installer that:
# - creates/uses venv
# - upgrades pip/setuptools/wheel
# - installs each requirement with retries
# - SKIPS packages that keep failing and continues to the end
# - prints a concise summary of successes/failures
# - exits 0 by default (so CI/deploy doesn’t stop), but you can flip STRICT mode.

set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQ_FILE="${PROJECT_DIR}/requirements.txt"
VENV_DIR="${PROJECT_DIR}/venv"
LOG_DIR="${PROJECT_DIR}/.install_logs"
LOG_FILE="${LOG_DIR}/install_$(date +%Y%m%d_%H%M%S).log"

RETRIES="${RETRIES:-3}"
SLEEP_SEC="${SLEEP_SEC:-3}"
STRICT="${STRICT:-0}" # 0: never fail the script; 1: exit 1 if anything failed

mkdir -p "$LOG_DIR"

echo "Python: $(python3 --version)"
echo "Script log: $LOG_FILE"
echo

# 1) Ensure venv
if [ ! -d "$VENV_DIR" ]; then
  echo "🐍 Creating venv at $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
fi
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
python -V
pip -V

echo "⬆️  Upgrading pip/setuptools/wheel..."
python -m pip install --upgrade pip setuptools wheel >>"$LOG_FILE" 2>&1 || true
echo

# 2) Basic build deps (quietly try; ignore errors)
if command -v apt-get >/dev/null 2>&1; then
  echo "🧱 (Best effort) installing build deps..."
  sudo apt-get update -y >>"$LOG_FILE" 2>&1 || true
  sudo apt-get install -y build-essential python3-dev libpq-dev >>"$LOG_FILE" 2>&1 || true
  echo
fi

if [ ! -f "$REQ_FILE" ]; then
  echo "❌ requirements.txt not found at $REQ_FILE"
  exit 1
fi

successes=()
failures=()

retry_pip () {
  local pkg="$1"
  local attempt=1
  while [ "$attempt" -le "$RETRIES" ]; do
    echo "📦 Installing: $pkg (attempt $attempt/$RETRIES)"
    if python -m pip install "$pkg" >>"$LOG_FILE" 2>&1; then
      echo "✅ Installed: $pkg"
      return 0
    else
      echo "⚠️  Failed: $pkg (attempt $attempt). Retrying in ${SLEEP_SEC}s..."
      sleep "$SLEEP_SEC"
    fi
    attempt=$((attempt+1))
  done
  return 1
}

echo "🧾 Installing packages from requirements.txt..."
while IFS= read -r raw; do
  line="$(echo "$raw" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"  # trim
  # Skip blanks / comments
  [[ -z "$line" || "$line" =~ ^# ]] && continue

  # Handle nested requirement files (-r other.txt)
  if [[ "$line" =~ ^-r[[:space:]]+(.+) ]]; then
    nested="${BASH_REMATCH[1]}"
    echo "🔁 Found nested requirements: $nested"
    while IFS= read -r subraw; do
      subline="$(echo "$subraw" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
      [[ -z "$subline" || "$subline" =~ ^# ]] && continue
      if retry_pip "$subline"; then
        successes+=("$subline")
      else
        echo "⏭️  Skipping after retries: $subline"
        failures+=("$subline")
      fi
    done < "$nested"
    continue
  fi

  # Known environment-specific package to skip when *not* using conda
  if [[ -z "${CONDA_PREFIX:-}" ]] && [[ "$line" =~ ^anaconda-anon-usage ]]; then
    echo "⏭️  Skipping $line (Anaconda-only; not needed in venv)" | tee -a "$LOG_FILE"
    continue
  fi

  # Try install with retries; never stop on failure
  if retry_pip "$line"; then
    successes+=("$line")
  else
    echo "⏭️  Skipping after retries: $line"
    failures+=("$line")
  fi
done < "$REQ_FILE"

echo
echo "====================== SUMMARY ======================"

if [ "${#successes[@]}" -gt 0 ]; then
  echo "✅ Installed (${#successes[@]}):"
  for s in "${successes[@]}"; do echo "  - $s"; done
else
  echo "✅ Installed: none"
fi

if [ "${#failures[@]}" -gt 0 ]; then
  echo
  echo "❌ Skipped after ${RETRIES} retries (${#failures[@]}):"
  for f in "${failures[@]}"; do echo "  - $f"; done
  echo
  echo "📜 See full logs at: $LOG_FILE"
fi

# Exit policy
if [ "$STRICT" -eq 1 ] && [ "${#failures[@]}" -gt 0 ]; then
  echo "🚫 STRICT=1 → exiting with code 1 due to failures."
  exit 1
fi

echo "🏁 Done."
exit 0