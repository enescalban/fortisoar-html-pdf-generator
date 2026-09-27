<p align="center">
  <img src="docs/logo.png" alt="HTML PDF Generator logo" width="100" height="100">
</p>

<h1 align="center">HTML PDF Generator — FortiSOAR Connector</h1>

<p align="center">
  Convert HTML or Rich Text content into a PDF file directly inside FortiSOAR playbooks.
</p>

---

## Overview

**HTML PDF Generator** is a utility connector for FortiSOAR. It takes HTML (or Rich Text) produced
in a playbook — an incident summary, an executive report, an email body — and renders it into a
PDF stored on the FortiSOAR appliance. The returned file path can be passed straight to the next
step (for example *Upload File* or *Create Attachment*).

It needs no external service and no configuration: rendering is done locally by whichever PDF
engine is installed on the appliance.

| | |
|---|---|
| **Version** | 2.2.0 |
| **Category** | Compliance and Reporting, Utilities |
| **Configuration** | None required |
| **Python dependencies** | None |

## Features

- Wraps HTML fragments into a full UTF-8 document automatically (Turkish and other non-ASCII text renders correctly).
- Page size (**A3, A4, A5, Letter, Legal**), **orientation** and **margins** are configurable.
- Four rendering engines with automatic fallback: **wkhtmltopdf → Chromium → Pandoc → LibreOffice**.
- Health check reports which engines are installed on the appliance.
- Safe, unique output file names — concurrent playbook runs never overwrite each other.
- Per-engine timeout, so a hung renderer can't block a playbook.
- Local file access is **disabled by default** to protect the appliance when rendering untrusted content (alerts, emails).

## Requirements

At least one of the following must be installed on the FortiSOAR appliance (or on the agent that runs the connector):

| Engine | Package | Notes |
|---|---|---|
| wkhtmltopdf | `wkhtmltopdf` | Fast, recommended default. |
| Chromium | `chromium` / `google-chrome` | Best support for modern CSS (flexbox, grid). |
| Pandoc | `pandoc` + a TeX distribution with `xelatex` | Good for text-heavy documents, limited CSS. |
| LibreOffice | `libreoffice` | Last-resort fallback; page options are best effort. |

Example (RHEL / Rocky based appliance):

```bash
sudo dnf install -y wkhtmltopdf
```

Run **Health Check** after installing the connector — it lists the engines it found.

## Installation

1. Download `HTMLPDFGenerator.tgz` from the [Releases](../../releases) page (or build it — see below).
2. In FortiSOAR go to **Content Hub → Create → Upload Connector** and select the `.tgz` file.
3. Open the connector, add a configuration (no fields are required) and run **Health Check**.

## Operation: Build PDF Document

### Parameters

| Parameter | Required | Default | Description |
|---|---|---|---|
| Data for PDF | Yes | — | HTML or Rich Text to convert. Fragments are wrapped in a full document; JSON objects are rendered as formatted text. |
| File Name | No | `report.pdf` | Output file name. Unsafe characters become `_`; `.pdf` is appended if missing. |
| Page Size | No | `A4` | `A3`, `A4`, `A5`, `Letter`, `Legal`. |
| Orientation | No | `Portrait` | `Portrait` or `Landscape`. |
| Margin | No | `0.75in` | Margin for all sides, e.g. `20mm`, `2cm`, `0.75in`. |
| Conversion Engine | No | `Auto` | `Auto` tries every installed engine in order; or force one engine. |
| Timeout (seconds) | No | `120` | Maximum time per engine attempt (1–900). |
| Allow Local File Access | No | `false` | Let the HTML load files from the appliance (e.g. `file:///tmp/logo.png`) when using wkhtmltopdf. Keep disabled for untrusted content. |

> Styles you put in your own HTML (including `@page` rules) take precedence over the page options above.

### Output

```json
{
  "status": "success",
  "_cyops_filepath": "/tmp/pdfgen_k2j9x1_incident_report.pdf",
  "file_path": "/tmp/pdfgen_k2j9x1_incident_report.pdf",
  "file_name": "incident_report.pdf",
  "mime_type": "application/pdf",
  "pdf_size_bytes": 48213,
  "engine": "wkhtmltopdf",
  "page_size": "A4",
  "orientation": "Portrait"
}
```

### Playbook example

1. **Build PDF Document**
   - Data for PDF: `{{vars.input.records[0].description}}`
   - File Name: `incident_{{vars.input.records[0].id}}.pdf`
2. Upload the generated file to FortiSOAR (e.g. the file upload action of the built-in *Utilities* connector) using `{{vars.steps.Build_PDF_Document.data.file_path}}`.
3. Create an attachment from the uploaded file and link it to the record.

## Building the package

```bash
tar -czf HTMLPDFGenerator.tgz HTMLPDFGenerator/
```

## Project layout

```
HTMLPDFGenerator/
├── info.json               # Connector metadata, operations and parameters
├── connector.py            # Connector entry point
├── builtins.py             # Operation registry (FortiSOAR generated)
├── build_pdf_document.py   # "Build PDF Document" operation
├── pdf_engines.py          # wkhtmltopdf / Chromium / Pandoc / LibreOffice back-ends
├── health_check.py         # Verifies at least one engine is installed
├── constants.py
├── requirements.txt        # No Python dependencies
└── images/
    ├── connector_logo_large.png   # 100 x 100
    └── connector_logo_small.png   # 32 x 32
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Health check: *No HTML to PDF engine found* | Install one of the engines listed in [Requirements](#requirements). |
| Images from the internet are missing | The appliance needs outbound access to those URLs, or embed images as `data:` URIs. |
| Local images (`file://`) are missing | Enable **Allow Local File Access** (wkhtmltopdf) — only for trusted HTML. |
| Layout looks different from the browser | Set **Conversion Engine** to `Chromium` for full modern CSS support. |
| Pandoc fails with a LaTeX error | Install the missing TeX packages or use another engine. |

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
