"""Shared constants for the HTML PDF Generator connector."""

LOGGER_NAME = 'html-pdf-generator'

# Directory where generated PDFs are written. FortiSOAR playbook steps
# (e.g. "Upload File" / "Create Attachment") can pick files up from here.
OUTPUT_DIR = '/tmp'

DEFAULT_FILE_NAME = 'report.pdf'
DEFAULT_PAGE_SIZE = 'A4'
DEFAULT_ORIENTATION = 'Portrait'
DEFAULT_MARGIN = '0.75in'
DEFAULT_TIMEOUT = 120  # seconds, per engine attempt
MAX_TIMEOUT = 900

SUPPORTED_PAGE_SIZES = ('A3', 'A4', 'A5', 'Letter', 'Legal')
SUPPORTED_ORIENTATIONS = ('Portrait', 'Landscape')

# Engine identifiers, in the order they are tried when engine is "Auto".
ENGINE_AUTO = 'Auto'
ENGINE_WKHTMLTOPDF = 'wkhtmltopdf'
ENGINE_CHROMIUM = 'Chromium'
ENGINE_PANDOC = 'Pandoc'
ENGINE_LIBREOFFICE = 'LibreOffice'
ENGINE_ORDER = (ENGINE_WKHTMLTOPDF, ENGINE_CHROMIUM, ENGINE_PANDOC, ENGINE_LIBREOFFICE)

# Executables looked up on PATH for each engine (first match wins).
ENGINE_EXECUTABLES = {
    ENGINE_WKHTMLTOPDF: ('wkhtmltopdf',),
    ENGINE_CHROMIUM: ('chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable',
                      'chrome', 'headless_shell'),
    ENGINE_PANDOC: ('pandoc',),
    ENGINE_LIBREOFFICE: ('libreoffice', 'soffice'),
}

# Margin must be a number followed by a unit understood by every engine.
MARGIN_PATTERN = r'^\s*\d+(\.\d+)?\s*(mm|cm|in)\s*$'
