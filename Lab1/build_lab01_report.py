"""Render lab01.md to a paginated PDF with locally installed Chromium."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

import markdown


ROOT = Path(__file__).resolve().parent
CSS = """
@page {
  size: A4;
  margin: 11mm 13mm 13mm;
  @bottom-left { content: 'SDR LABORATORY   /   TEAM 01'; color: #487180; font: 8pt 'Segoe UI', sans-serif; }
  @bottom-right { content: counter(page) ' / ' counter(pages); color: #487180; font: 8pt 'Segoe UI', sans-serif; }
}
* { box-sizing: border-box; }
body { color: #152a34; font: 10pt/1.31 'Segoe UI', Arial, sans-serif; margin: 0; }
h1, h2, h3 { margin: 0; color: #102f40; line-height: 1.15; break-after: avoid; }
h1 { font-size: 30pt; letter-spacing: -.7pt; margin-bottom: 2.5mm; }
h2 { border-top: 2pt solid #167b77; padding-top: 2.5mm; margin-bottom: 2.5mm; font-size: 19pt; }
h3 { margin-top: 3mm; margin-bottom: 1.2mm; font-size: 12.1pt; }
p { margin: 0 0 2.1mm; orphans: 2; widows: 2; }
p:has(+ table) { break-after: avoid; }
a { color: #155d82; text-decoration: none; }
ul, ol { margin: 0 0 2.5mm; padding-left: 6mm; }
li { margin-bottom: 1mm; }
table { width: 100%; border-collapse: collapse; margin: 2mm 0 3mm; font-size: 9pt; line-height: 1.32; }
thead { background: #e6f0f1; }
th, td { padding: 1.05mm 1.5mm; vertical-align: top; text-align: left; border-bottom: 1px solid #d6e3e6; }
tbody tr:nth-child(even) { background: #f5f8fa; }
tr { break-inside: avoid; }
code { font: .9em Consolas, monospace; overflow-wrap: anywhere; }
blockquote { background: #edf5f5; border-left: 2pt solid #167b77; margin: 3mm 0; padding: 2.3mm 3mm; }
blockquote p { margin: 0; }
figure { margin: 2mm 0 3mm; break-inside: avoid; }
figure img { width: 100%; display: block; }
figcaption { font-size: 8.7pt; line-height: 1.34; color: #3a5664; margin-top: 1mm; }
.kicker { color: #167b77; font-size: 9pt; font-weight: 650; letter-spacing: 1.3pt; margin: 0 0 2.5mm; }
.byline { font-size: 10.4pt; color: #486574; margin-bottom: 3.5mm; }
p:has(> .report-download) { display: none; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 2mm; align-items: start; }
.two > img { border: 1px solid #d6e3e6; }
.two > figcaption { grid-column: 1 / -1; }
.setup img:last-of-type { grid-column: 1 / -1; max-height: 23mm; object-fit: contain; }
.loop img { max-height: 30mm; object-fit: contain; }
.sweeps img { max-height: 43mm; object-fit: contain; }
.wide img { max-height: 83mm; object-fit: contain; }
.keyfob-live img { max-height: 43mm; object-fit: contain; }
.burst img { max-height: 54mm; object-fit: contain; }
.page-break { break-before: page; }
"""


def find_browser():
    for name in ('chromium', 'google-chrome', 'chrome', 'msedge'):
        if path := shutil.which(name):
            return Path(path)
    for key in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
        if folder := os.environ.get(key):
            for executable in ('Google/Chrome/Application/chrome.exe', 'Microsoft/Edge/Application/msedge.exe'):
                path = Path(folder) / executable
                if path.is_file():
                    return path
    raise SystemExit('Chrome, Edge or Chromium is required. Use --browser PATH.')


def build(browser, output):
    body = markdown.markdown((ROOT / 'lab01.md').read_text(encoding='utf-8'),
                             extensions=['tables', 'md_in_html', 'attr_list'])
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<title>Lab 01 — RF Spectrum Monitoring</title>'
            f'<base href="{ROOT.as_uri()}/"><style>{CSS}</style></head><body>{body}</body></html>')
    with TemporaryDirectory(prefix='lab01_print_', dir=ROOT) as work:
        temp = Path(work)
        document = temp / 'report.html'
        document.write_text(html, encoding='utf-8')
        pdf = temp / 'rendered.pdf'
        command = [str(browser), '--headless', '--disable-gpu', '--disable-crash-reporter',
                   '--no-pdf-header-footer', f'--user-data-dir={temp / "profile"}',
                   f'--print-to-pdf={pdf}', document.as_uri()]
        run = subprocess.run(command, capture_output=True, text=True, timeout=55)
        if run.returncode or not pdf.is_file() or pdf.stat().st_size == 0:
            raise SystemExit(f'PDF rendering failed.\n{run.stdout}\n{run.stderr}')
        shutil.copyfile(pdf, output)
    print(f'Wrote {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', type=Path, help='path to the Chromium-based browser')
    parser.add_argument('--output', type=Path, default=ROOT / 'SDR_Lab1_report.pdf')
    options = parser.parse_args()
    build(options.browser or find_browser(), options.output.resolve())
