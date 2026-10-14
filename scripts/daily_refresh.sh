#!/usr/bin/env bash
# Host cron helper — more reliable than relying only on the in-process 7AM loop.
# Example crontab (Pakistan ~02:00 UTC = 07:00 PKT in standard time; adjust for DST if needed):
#   0 2 * * * /path/to/climate-tender-finder/scripts/daily_refresh.sh >> /var/log/news-tracker-ingest.log 2>&1
#
# Or call at 07:00 local on a Pakistan-timezone server:
#   0 7 * * * /path/to/scripts/daily_refresh.sh

set -euo pipefail
API_BASE="${API_BASE:-http://127.0.0.1:3001/api}"
echo "$(date -Is) POST ${API_BASE}/feeds/refresh"
curl -fsS -X POST "${API_BASE}/feeds/refresh"
echo
echo "$(date -Is) done"
