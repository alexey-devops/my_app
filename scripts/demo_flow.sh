#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-https://localhost:8443}"

post_task() {
  local title="$1"
  curl -skS -X POST "${BASE_URL}/api/tasks" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"${title}\"}"
}

patch_status() {
  local task_id="$1"
  local status="$2"
  curl -skS -X PATCH "${BASE_URL}/api/tasks/${task_id}/status" \
    -H "Content-Type: application/json" \
    -d "{\"status\":\"${status}\"}"
}

extract_id() {
  jq -r '.id // empty'
}

echo "Demo flow start against ${BASE_URL}"
echo "1) Creating tasks..."

T1_JSON="$(post_task "Demo: onboarding pipeline")"
echo "$T1_JSON"
T1_ID="$(echo "$T1_JSON" | extract_id)"
sleep 2

T2_JSON="$(post_task "Demo: integration with payment [FAIL]")"
echo "$T2_JSON"
T2_ID="$(echo "$T2_JSON" | extract_id)"
sleep 2

T3_JSON="$(post_task "Demo: analytics backfill")"
echo "$T3_JSON"
T3_ID="$(echo "$T3_JSON" | extract_id)"
sleep 2

echo "2) Manual status changes through API (extra lifecycle events)..."
if [[ -n "${T3_ID}" ]]; then
  patch_status "$T3_ID" "in_progress"
  sleep 2
  patch_status "$T3_ID" "pending"
fi

echo
echo "Demo flow completed."
echo "Watch in Grafana:"
echo "- Application Lifecycle & Logs: live API/worker streams + activity panels"
echo "- Service Command Center: External API via Nginx, critical logs"

