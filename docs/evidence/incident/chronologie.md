# Incident timeline (task 7.2)

Incident played on Saturday, November 21, 2026, on the `t7-2-incident` branch. Real times are Paris time.
Data: real NYC yellow taxi trips (TLC), replayed against the API with `replay.py`.

**Starting state**: `taxi-demand` v1 in `@production` (the model trained on real data in task 7.1). `data/truth.csv`, `data/decisions.jsonl` and `data/promotions.jsonl` deleted before starting. MLflow, the API and the Prometheus, Alertmanager and Grafana stack running.

| Real time | Simulated date | Step | What was observed | Evidence |
|---|---|---|---|---|
| ≈ 16:31:30 → 16:35:30 | Feb 17 → 29, 2020 | February replay (normal period) | Highest PSI ≈ 0.07 on `lag_1h` and ≈ 0.095 on `lag_24h`, far below the 0.25 threshold. No alert. | `t7.2_psi_fevrier.png` |
| ≈ 16:37 → 16:43 | Mar 1 → 31, 2020 | March replay at 2 simulated hours per second | The PSI stays below 0.25 early in the month, with one brief spike above the threshold (≈ 0.55 on `lag_1h`, around March 11) that does not last long enough to trigger the alert. | `t7.2_psi_mars.png` |
| ≈ 16:39:45 | ≈ Mar 14, 2020 | Threshold crossed for good | Both PSIs go above 0.25 and stay there; they climb to ≈ 7.7–8 by the end of the month (New York lockdown). | `t7.2_psi_mars.png` |
| ≈ 16:40:30 | ≈ mid-March 2020 | `InputDrift` goes from pending to **firing** | In the 16:45 screenshot, the alert had been active for 5 min 34 s (`lag_1h`) and 5 min 24 s (`lag_24h`), with PSI values of 7.88 and 7.76. The rule waits 1 minute above 0.25 (`for: 1m`). | `t7.2_inputdrift_firing.png` |
| 16:46:14 → 16:46:16 | Mar 31, 2020, 23:00 | `check_and_retrain.py`: **retrain** decision | 7-day window, PSI of 7.70 (`lag_1h`) and 7.64 (`lag_24h`). Candidate trained on the recent days (run `dashing-shrew-758`, `1cfafc7ee99441fb998ac19c65ec26d5`). Gate passed: MAE of 3.97 vs 21.68 for production on the last 2 days, 82% better (threshold: 5%). Registered as **v2 `@staging`** at 16:46:16. | `t7.2_check_and_retrain.png`, `t7.2_v2_staging.png` |
| ≈ 16:48 | Mar 31, 2020, 23:00 | `check_and_retrain.py` run again immediately: **cooldown** | Same PSI, but a retrain had just happened (less than 7 days earlier): no new candidate. | `t7.2_cooldown.png` |
| 16:48:55 | — | `promote.py`: human decision to promote | `@production` moves from v1 to v2 (line `{"from": "1", "to": "2"}` in `promotions.jsonl`), then the API is restarted. | `promotions.jsonl` |
| ≈ 16:51 | — | Check after promotion | `/health` returns `{"status": "ok", "model_version": "2"}`: the API serves the new model. | `t7.2_health_v2.png` |
| ≈ 16:52 | — | `rollback.py`: timed rollback | `@production` goes back to v1; after the API restart, `/health` shows v1 after **22.4 s** (target: under 300 s). | `t7.2_rollback.png` |
| 16:53 | — | Evidence filed | `decisions.jsonl` and `promotions.jsonl` copied to `docs/evidence/incident/`. | `decisions.jsonl`, `promotions.jsonl` |

## Key figures

- **Detection**: input drift around March 14, 2020 (simulated date), `InputDrift` firing about 1 minute later.
- **Retraining**: candidate MAE 3.97 vs 21.68 for production, 82% better.
- **Promotion**: v1 → v2 at 16:48:55, by a person, never by the script.
- **Rollback**: 22.4 s, from the command until `/health` shows v1.
- **Cooldown**: a second `check_and_retrain.py` right afterwards did not start another training run.

## How the times were established

- **Exact** (script output and files): 16:46:14–16:46:16 (MLflow log and v2 registration time), 16:48:55 (`promotions.jsonl`, 15:48:55 UTC), 22.4 s (`rollback.py` output), 16:53 (time the `.jsonl` copies were made).
- **Read from the Grafana charts**: start and end of the replays, threshold crossing (≈ 16:39:45).
- **Estimated**: the simulated date of the crossing, from the replay speed (2 simulated hours per second, about 12 s per day). It matches the task 7.1 rehearsal, where the threshold was crossed around March 13–14. Terminal screenshots are timestamped to the minute.
