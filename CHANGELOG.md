# Changelog

## 2.2.0

### Added
- New optional parameters: **Page Size**, **Orientation**, **Margin**, **Conversion Engine**, **Timeout** and **Allow Local File Access**.
- Output now includes `file_path`, `engine`, `page_size` and `orientation`.
- Health check verifies that at least one PDF engine is installed and lists the engines found.
- New connector icons (100x100 and 32x32).
- JSON objects passed as *Data for PDF* are rendered as formatted text.

### Changed
- Rendering engines moved to `pdf_engines.py`; engines are located with `shutil.which` instead of trial execution.
- Output files are created with `tempfile.mkstemp` (no private `tempfile` APIs), guaranteeing unique names.
- Chromium and LibreOffice run with isolated temporary profiles, so parallel playbook runs don't conflict.
- wkhtmltopdf exiting non-zero on harmless warnings no longer fails the conversion when a valid PDF was produced.
- Clearer error messages that include each engine's failure reason.
- Unknown operations raise a proper `ConnectorError`.

### Security
- Local file access is disabled by default for wkhtmltopdf (previously always enabled).
- File names are sanitised against path traversal.
- Every engine call has a timeout and cannot block on interactive prompts.

### Removed
- Unused REST template (`utils.py`) and the `requests` dependency.

## 2.1.0
- Initial public version.
