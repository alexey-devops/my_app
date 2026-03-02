#!/usr/bin/env bash
set -euo pipefail

if command -v helm >/dev/null 2>&1; then
  exec helm "$@"
fi

KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"
if [[ ! -f "$KUBECONFIG_PATH" ]]; then
  echo "KUBECONFIG not found at $KUBECONFIG_PATH" >&2
  exit 1
fi

mkdir -p "$HOME/.config/helm" "$HOME/.cache/helm" "$HOME/.local/share/helm"

exec docker run --rm \
  --network host \
  -v "$KUBECONFIG_PATH:/root/.kube/config:ro" \
  -v "$HOME/.config/helm:/root/.config/helm" \
  -v "$HOME/.cache/helm:/root/.cache/helm" \
  -v "$HOME/.local/share/helm:/root/.local/share/helm" \
  -v "$(pwd):/work" \
  -w /work \
  alpine/helm:3.15.4 "$@"
