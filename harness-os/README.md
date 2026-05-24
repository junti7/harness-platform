# Harness-OS Local Runtime

## 1) Security + CORS

Set these in repository `.env`:

- `HARNESS_OS_SECRET_KEY=<random-long-secret>`
- `HARNESS_OS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173`
- `HARNESS_OS_CACHE_SECONDS=60`

Set this in `harness-os/frontend/.env`:

- `VITE_HARNESS_OS_API_BASE=http://127.0.0.1:8000`
- `VITE_HARNESS_OS_SECRET=<same secret as HARNESS_OS_SECRET_KEY>`

## 2) Local run commands

```bash
./harness-os/scripts/start_local.sh
```

Stop:

```bash
./harness-os/scripts/stop_local.sh
```

## 3) launchd (macOS)

Register persistent services:

```bash
./harness-os/scripts/register_launchd.sh
```

Maily CSV sync uses `com.harness.maily-metrics-sync.plist` and runs daily at `23:05`.
Before loading it, update `MAILY_METRICS_CSV_PATH` inside the plist or export the same path in your shell wrapper flow.

Manual run:

```bash
source .venv/bin/activate
python scripts/sync_maily_metrics.py --date $(date +%F) --csv data/maily_metrics.sample.csv
```

Weekly issue package for Maily:

```bash
source .venv/bin/activate
python scripts/publish_weekly_to_maily.py --issue 1 --date $(date +%F)
```

After manual publish on Maily, record status:

```bash
source .venv/bin/activate
python scripts/publish_weekly_to_maily.py \
  --issue 1 \
  --date $(date +%F) \
  --mark-published \
  --public-url https://maily.so/...
```

Unregister:

```bash
launchctl unload ~/Library/LaunchAgents/com.harness.harness-os-backend.plist
launchctl unload ~/Library/LaunchAgents/com.harness.harness-os-frontend.plist
launchctl unload ~/Library/LaunchAgents/com.harness.maily-metrics-sync.plist
```

## 4) URLs

- Frontend: `http://127.0.0.1:5173`
- Backend health: `http://127.0.0.1:8000/api/health`
