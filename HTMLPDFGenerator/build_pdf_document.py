"""Operation: Build PDF Document.

Converts HTML / Rich Text content into a PDF file stored on the FortiSOAR
appliance so the next playbook step can attach or upload it.
"""
import html
import json
import os
import re
import tempfile

from connectors.core.connector import get_logger, ConnectorError

from .constants import (LOGGER_NAME, OUTPUT_DIR, DEFAULT_FILE_NAME, DEFAULT_PAGE_SIZE,
                        DEFAULT_ORIENTATION, DEFAULT_MARGIN, DEFAULT_TIMEOUT, MAX_TIMEOUT,
                        SUPPORTED_PAGE_SIZES, SUPPORTED_ORIENTATIONS, MARGIN_PATTERN,
                        ENGINE_AUTO, ENGINE_ORDER)
from .pdf_engines import ENGINES, find_executable

logger = get_logger(LOGGER_NAME)

_HEAD_OPEN = re.compile(r'<head[^>]*>', re.IGNORECASE)
_HTML_OPEN = re.compile(r'<html[^>]*>', re.IGNORECASE)


# --------------------------------------------------------------------------- #
# Parameter handling
# --------------------------------------------------------------------------- #
def _safe_filename(name):
    """Return a filesystem-safe file name that always ends with ``.pdf``."""
    name = os.path.basename(str(name or '').strip()) or DEFAULT_FILE_NAME
    if not name.lower().endswith('.pdf'):
        name += '.pdf'
    name = re.sub(r'[^A-Za-z0-9._-]+', '_', name).lstrip('.')
    if not name or name.lower() == 'pdf':
        return DEFAULT_FILE_NAME
    return name[-150:]  # keep well below filesystem limits


def _choice(value, allowed, default, label):
    """Case-insensitive match of ``value`` against ``allowed``; returns the canonical spelling."""
    if value in (None, ''):
        return default
    for option in allowed:
        if str(value).strip().lower() == option.lower():
            return option
    raise ConnectorError('Invalid {0} "{1}". Allowed values: {2}'.format(label, value, ', '.join(allowed)))


def _parse_options(params):
    margin = str(params.get('margin') or DEFAULT_MARGIN).strip()
    if not re.match(MARGIN_PATTERN, margin):
        raise ConnectorError('Invalid margin "{0}". Use a number with mm, cm or in (e.g. 20mm, 0.75in).'
                             .format(margin))

    timeout = params.get('timeout') or DEFAULT_TIMEOUT
    try:
        timeout = int(timeout)
    except (TypeError, ValueError):
        raise ConnectorError('Timeout must be an integer number of seconds')
    if not 1 <= timeout <= MAX_TIMEOUT:
        raise ConnectorError('Timeout must be between 1 and {0} seconds'.format(MAX_TIMEOUT))

    return {
        'page_size': _choice(params.get('pageSize'), SUPPORTED_PAGE_SIZES, DEFAULT_PAGE_SIZE, 'page size'),
        'orientation': _choice(params.get('orientation'), SUPPORTED_ORIENTATIONS, DEFAULT_ORIENTATION,
                               'orientation'),
        'margin': margin.replace(' ', ''),
        'engine': _choice(params.get('engine'), (ENGINE_AUTO,) + ENGINE_ORDER, ENGINE_AUTO, 'engine'),
        'timeout': timeout,
        'allow_local_files': str(params.get('allowLocalFileAccess', False)).lower() in ('true', '1', 'yes'),
    }


# --------------------------------------------------------------------------- #
# HTML preparation
# --------------------------------------------------------------------------- #
def _to_html(data):
    """Normalise playbook input into an HTML string.

    Playbooks sometimes pass a dict/list (e.g. a raw Jinja variable) instead of
    HTML; render those as pretty-printed JSON rather than a Python repr.
    """
    if isinstance(data, (dict, list)):
        return '<pre>{0}</pre>'.format(html.escape(json.dumps(data, indent=2, ensure_ascii=False, default=str)))
    return str(data)


def _prepare_html(content, options):
    """Wrap fragments in a full document and inject UTF-8 + default @page rules.

    The injected rules go at the very top of <head>, so any @page / style rules
    supplied by the user still take precedence.
    """
    page_css = '@page {{ size: {0} {1}; margin: {2}; }}'.format(
        options['page_size'], options['orientation'].lower(), options['margin'])
    injected = '<meta charset="UTF-8"><style>{0}</style>'.format(page_css)

    if not re.search(r'<html[\s>]', content, re.IGNORECASE):
        return '<!DOCTYPE html>\n<html><head>{0}</head><body>{1}</body></html>'.format(injected, content)
    if _HEAD_OPEN.search(content):
        return _HEAD_OPEN.sub(lambda m: m.group(0) + injected, content, count=1)
    return _HTML_OPEN.sub(lambda m: m.group(0) + '<head>' + injected + '</head>', content, count=1)


def _write_temp_html(content):
    fd, path = tempfile.mkstemp(prefix='pdfgen_', suffix='.html')
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        handle.write(content)
    return path


# --------------------------------------------------------------------------- #
# Conversion
# --------------------------------------------------------------------------- #
def html_to_pdf(html_content, output_path, options):
    """Render ``html_content`` into ``output_path`` and return the engine name used."""
    engines = ENGINE_ORDER if options['engine'] == ENGINE_AUTO else (options['engine'],)
    html_path = _write_temp_html(_prepare_html(html_content, options))
    errors = []
    try:
        for engine in engines:
            executable = find_executable(engine)
            if not executable:
                errors.append('{0}: not installed'.format(engine))
                logger.debug('%s is not installed, skipping', engine)
                continue
            try:
                logger.info('Converting HTML to PDF with %s (%s)', engine, executable)
                if os.path.exists(output_path):
                    os.remove(output_path)  # never report a stale file from a previous attempt
                ENGINES[engine](executable, html_path, output_path, options)
                if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
                    logger.info('PDF created with %s: %s', engine, output_path)
                    return engine
                errors.append('{0}: produced an empty file'.format(engine))
            except Exception as exc:  # try the next engine
                errors.append('{0}: {1}'.format(engine, exc))
                logger.warning('%s conversion failed: %s', engine, exc)
        raise ConnectorError('HTML to PDF conversion failed. ' + ' | '.join(errors))
    finally:
        if os.path.exists(html_path):
            os.remove(html_path)


def generate_pdf(config, params, *args, **kwargs):
    data = params.get('dataForPDF')
    if data is None or (isinstance(data, str) and not data.strip()):
        raise ConnectorError('No data provided for PDF conversion')

    options = _parse_options(params)
    file_name = _safe_filename(params.get('fileName'))

    # Unique path in OUTPUT_DIR so concurrent playbook runs never overwrite each other.
    fd, output_path = tempfile.mkstemp(prefix='pdfgen_', suffix='_' + file_name, dir=OUTPUT_DIR)
    os.close(fd)

    try:
        engine = html_to_pdf(_to_html(data), output_path, options)
    except Exception:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise

    return {
        'status': 'success',
        '_cyops_filepath': output_path,
        'file_path': output_path,
        'file_name': file_name,
        'mime_type': 'application/pdf',
        'pdf_size_bytes': os.path.getsize(output_path),
        'engine': engine,
        'page_size': options['page_size'],
        'orientation': options['orientation'],
    }
