# Health Import Source Evaluation

Reviewed on 2026-06-22 against Garmin developer documentation.

## Implemented Path

RunStats now supports local JSON health payload imports and direct provider
health exports when a provider capability probe reports support. Imported raw
health payloads are retained locally under the configured raw archive path and
normalized into `health_metrics`.

This keeps Phase 7 usable without Garmin credentials, hosted services, or a
physical watch health-export adapter.

## Canonical Metrics and Units

| Metric | Canonical unit |
| --- | --- |
| `steps` | `count` |
| `resting_hr` | `bpm` |
| `hrv` | `ms` |
| `sleep` | `hours` |
| `stress` | `score` |
| `body_battery` | `score` |
| `respiration` | `breaths/min` |
| `pulse_ox` | `percent` |

## Source Comparison

| Source | Privacy and credentials | Platform support | Approval or access | Recommendation |
| --- | --- | --- | --- | --- |
| Local folder/import fixtures | No network transfer and no Garmin credentials. Raw files stay in the local archive. | Desktop-local Python/FastAPI path. | No vendor approval. | Use now as the bootstrap and replay path for health JSON payloads. |
| Garmin Health SDK | Can remove Garmin server dependency for the Standard SDK path, but introduces mobile app/device management scope. | Garmin documents Android and iOS SDK support. | Enterprise request flow; evaluation is free, commercial use requires a license fee or device commitment. | Keep as a future mobile companion option, not the desktop bootstrap. |
| Garmin Connect Developer Program Health API | Uses Garmin Connect after user consent and OAuth 2.0; data moves through Garmin Connect before RunStats could ingest it. | REST JSON APIs for Garmin Connect uploaded data. | Enterprise/business-use program review; some commercial metric access can require fees. | Consider only if a future hosted/OAuth integration is acceptable to the local-first product. |
| Garmin Connect based adapters | Usually require user Garmin Connect credentials or session handling outside official RunStats contracts. | Adapter-dependent and not part of this repository. | Not an official integration path for this product. | Do not implement now; revisit only with explicit user approval and credential/privacy design. |

## Official Source Notes

- Garmin Connect Health API lists all-day metrics including steps, heart rate,
  sleep, stress, pulse ox, Body Battery, and respiration, delivered as JSON
  after Garmin Connect upload and approval:
  https://developer.garmin.com/gc-developer-program/health-api/
- Garmin Connect Developer Program FAQ says the program is for enterprise or
  business use, uses OAuth 2.0, and has an approval process:
  https://developer.garmin.com/gc-developer-program/program-faq/
- Garmin Health SDK FAQ says SDKs are enterprise-oriented, support Android and
  iOS over BLE, and commercial use requires a license fee or device commitment:
  https://developer.garmin.com/health-sdk/questions-answers/

## Backlog Recommendation

For the next health-source backlog item, prefer extending the local JSON import
fixtures into a documented export-folder workflow. Defer Garmin Health SDK and
Garmin Connect Developer Program integrations until RunStats intentionally adds
mobile-app or OAuth credential flows.
