# RunStats Documentation

This folder contains user, developer, packaging, privacy, and domain notes for
RunStats. The root README explains the repository as a whole; these documents
go deeper on how to use, run, validate, and reason about the app.

## File Inventory

| Path | Purpose |
| --- | --- |
| `.gitkeep` | Keeps the documentation directory present even when no generated docs exist. |
| `README.md` | Documentation folder overview and file inventory. |
| `chat-assistant.md` | Chat assistant architecture, local provider configuration, grounding rules, and safety notes. |
| `health-import-sources.md` | Supported health metric sources, normalized metric names, units, and import expectations. |
| `local-desktop-package.md` | Notes for building and running the combined local production app. |
| `local-setup.md` | Developer and real-device setup guide, including backend/frontend startup, database preparation, watch discovery, FIT import, validation, and troubleshooting. |
| `privacy-and-data-management.md` | Local-first data storage model, export format, delete controls, and hosted-data considerations. |
| `user-guide.md` | End-user guide for using the app after it has been installed and started. |

## Reading Order

For end users:

1. `user-guide.md`
2. `privacy-and-data-management.md`

For developers:

1. `../README.md`
2. `local-setup.md`
3. `../backend/README.md`
4. `../frontend/README.md`

For product or architecture context:

1. `../runstats-design.md`
2. `../runstats-product-backlog.md`
3. `chat-assistant.md`
4. `health-import-sources.md`
