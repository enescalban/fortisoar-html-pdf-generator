"""HTML -> PDF rendering back-ends.

Each engine function has the signature ``fn(executable, html_path, output_path, options)``
and must write a PDF to ``output_path``. The caller verifies the output file,
so engines only need to raise when something clearly went wrong.
"""
import os
import shutil
import subprocess
import tempfile

from connectors.core.connector import get_logger, ConnectorError

from .constants import (LOGGER_NAME, ENGINE_EXECUTABLES, ENGINE_WKHTMLTOPDF, ENGINE_CHROMIUM,
                        ENGINE_PANDOC, ENGINE_LIBREOFFICE)

logger = get_logger(LOGGER_NAME)


def find_executable(engine):
    """Return the absolute path of the first executable found for ``engine``, or None."""
    for name in ENGINE_EXECUTABLES.get(engine, ()):
        path = shutil.which(name)
        if path:
            return path
    return None


def available_engines():
    """Return ``{engine_name: executable_path}`` for every engine installed on this host."""
    found = {}
    for engine in ENGINE_EXECUTABLES:
        path = find_executable(engine)
        if path:
            found[engine] = path
    return found


def _run(cmd, timeout, cwd=None):
    """Run a command, returning the CompletedProcess. Never raises on non-zero exit codes,
    because some engines (notably wkhtmltopdf) exit non-zero on harmless warnings
    while still producing a valid PDF."""
    logger.debug('Executing: %s', ' '.join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd,
                                stdin=subprocess.DEVNULL)  # never block on interactive prompts
    except subprocess.TimeoutExpired:
        raise ConnectorError('Timed out after {0} seconds'.format(timeout))
    if result.returncode != 0:
        logger.warning('Command exited with code %s: %s', result.returncode, _tail(result.stderr))
    return result


def _tail(text, limit=500):
    text = (text or '').strip()
    return text if len(text) <= limit else '...' + text[-limit:]


def _raise_if_no_output(result, output_path):
    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        detail = _tail(result.stderr) or _tail(result.stdout) or 'no output produced'
        raise ConnectorError('exit code {0}: {1}'.format(result.returncode, detail))


def wkhtmltopdf(executable, html_path, output_path, options):
    cmd = [
        executable, '--quiet',
        '--page-size', options['page_size'],
        '--orientation', options['orientation'],
        '--margin-top', options['margin'], '--margin-right', options['margin'],
        '--margin-bottom', options['margin'], '--margin-left', options['margin'],
        '--encoding', 'UTF-8',
        '--enable-local-file-access' if options['allow_local_files'] else '--disable-local-file-access',
        html_path, output_path,
    ]
    _raise_if_no_output(_run(cmd, options['timeout']), output_path)


def chromium(executable, html_path, output_path, options):
    # Page size / orientation / margins are injected as a CSS @page rule
    # (see build_pdf_document._prepare_html), which Chromium honours.
    profile_dir = tempfile.mkdtemp(prefix='pdfgen_chrome_')
    try:
        cmd = [
            executable, '--headless', '--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage',
            '--disable-extensions', '--no-first-run', '--hide-scrollbars',
            '--user-data-dir=' + profile_dir,
            '--no-pdf-header-footer', '--print-to-pdf-no-header',  # new + legacy flag names
            '--run-all-compositor-stages-before-draw', '--virtual-time-budget=10000',
            '--print-to-pdf=' + output_path,
            'file://' + os.path.abspath(html_path),
        ]
        _raise_if_no_output(_run(cmd, options['timeout']), output_path)
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)


def pandoc(executable, html_path, output_path, options):
    geometry = 'margin=' + options['margin'].replace(' ', '')
    cmd = [
        executable, html_path, '-f', 'html', '-t', 'pdf', '-o', output_path,
        '--pdf-engine=xelatex',
        '-V', 'papersize=' + options['page_size'].lower(),
        '-V', 'geometry:' + geometry,
    ]
    if options['orientation'] == 'Landscape':
        cmd += ['-V', 'geometry:landscape']
    _raise_if_no_output(_run(cmd, options['timeout']), output_path)


def libreoffice(executable, html_path, output_path, options):
    # Isolated profile + output dir so parallel playbook runs don't collide.
    work_dir = tempfile.mkdtemp(prefix='pdfgen_lo_')
    try:
        profile_uri = 'file://' + os.path.join(work_dir, 'profile')
        cmd = [
            executable, '-env:UserInstallation=' + profile_uri, '--headless', '--norestore',
            '--convert-to', 'pdf:writer_web_pdf_Export', '--outdir', work_dir, html_path,
        ]
        result = _run(cmd, options['timeout'])
        generated = os.path.join(work_dir, os.path.splitext(os.path.basename(html_path))[0] + '.pdf')
        if not os.path.isfile(generated):
            raise ConnectorError('exit code {0}: {1}'.format(
                result.returncode, _tail(result.stderr) or 'LibreOffice did not create a PDF'))
        shutil.move(generated, output_path)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


ENGINES = {
    ENGINE_WKHTMLTOPDF: wkhtmltopdf,
    ENGINE_CHROMIUM: chromium,
    ENGINE_PANDOC: pandoc,
    ENGINE_LIBREOFFICE: libreoffice,
}
