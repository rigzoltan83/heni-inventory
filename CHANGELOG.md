# Changelog

All notable changes to Username's Inventory will be documented in this file.

## [0.1.0-alpha.1] - 2026-09-04

### Added

- Hierarchical storage locations.
- Item master data and item types.
- Inventory receipt, movement, issue and correction workflows.
- Current stock overview by item and storage location.
- Inventory movement history.
- CSV and XLSX stock exports.
- CSV and XLSX movement exports.
- Item image support.
- Barcode and label related workflows.
- Scanner-oriented inventory interface.
- Administrator, editor and viewer roles.
- User administration.
- Hungarian and English interface support.
- Per-user preferred language.
- PostgreSQL database with Alembic/Flask-Migrate migrations.
- Health endpoint for application and database checks.

### Changed

- Public application branding changed from Heni Inventory to Username's Inventory.
- Export filenames were generalized for public use.
- Item upload storage is now configurable and no longer tied to a specific installation path.

### Security / repository hygiene

- Local production backup scripts are excluded from the public repository.
- Private initial inventory data is excluded from the public repository.
- Environment files and uploads remain ignored by Git.
