"""Attach the shared Gridline site shell without rewriting media or script content.

The hourly publisher uses this same adapter as the existing static reports.
Only Python's standard library is required on the publishing machine.
"""
from html import escape, unescape
from pathlib import Path
import re

VERSION = '2026-09-09-sites'


def project_identity(site: str) -> str:
    """Project-specific identity and useful destinations, shared by every report."""
    base = 'https://thereprocase.github.io/' + site + '/'
    records = {
        'dell-5560-wall-mount': ('DESIGN JOURNAL / CAD + FLOW', 'Laptop wall mount', 'Minimalist mounting and ducted cooling, with the geometry and airflow evidence together.', [('Explore the designs', base), ('Latest flow videos', base + 'simulation/revh-transient/sequence/')]),
        '5680-dock': ('DESK HARDWARE / D8 PROTOTYPE', 'Precision 5680 dock', 'A serviceable printed dock: recessed fans, captured connectors and adjustable hardware.', [('Current D8 design', base), ('Open the CAD viewer', base + 'desk-dock.html?rev=D8#model')]),
        'onshape-reference-align': ('CALIBRATION WORKBENCH / IMAGE + GEOMETRY', 'Reference Align', 'Known distances. Independent directions. Reference images placed with intent.', [('Download the app', base + '#downloads'), ('Read the setup guide', base + 'START-HERE.html')]),
        'claude-usage': ('LOCAL TRANSCRIPT ANALYSIS / 90 DAYS', 'Claude Usage', 'Read your usage history from the data already on your machine.', [('Installation guide', base + '#gl-section-3'), ('Companion status line', 'https://thereprocase.github.io/claude-statusline/')]),
    }
    if site not in records:
        return ''
    kind, title, description, links = records[site]
    return (f'<div class="gl-project-identity"><div><span class="gl-identity-type">{escape(kind)}</span>'
            f'<strong>{escape(title)}</strong><p>{escape(description)}</p></div><nav class="gl-identity-actions" aria-label="Project resources">'
            + ''.join(f'<a class="gl-button" href="{escape(url)}">{escape(label)} ↗</a>' for label, url in links) + '</nav></div>')


def apply_gridline(document: str, page_path: Path, site='dell-5560-wall-mount', public_root=None) -> str:
    if 'data-gridline=' in document:
        return document
    page_path = Path(page_path)
    public_root = Path(public_root) if public_root else Path(__file__).resolve().parents[2] / 'docs'
    relative = page_path.relative_to(public_root)
    prefix = '../' * (len(relative.parts) - 1)
    kind = 'gl-cfd' if 'simulation' in relative.parts else 'gl-reference' if site == 'onshape-reference-align' else 'gl-usage' if site == 'claude-usage' else 'gl-cad'
    labels = {'dell-5560-wall-mount': 'LAPTOP WALL MOUNT / DESIGN JOURNAL', '5680-dock': 'PRECISION 5680 / DESK DOCK', 'onshape-reference-align': 'REFERENCE ALIGN / ONShape'.upper(), 'claude-usage': 'CLAUDE USAGE / LOCAL TRANSCRIPT TOOLS'}
    label = labels.get(site, site.upper())
    # Several original CFD documents intentionally omitted optional head/body tags.
    # Make them explicit before inserting the common shell, keeping scripts intact.
    if not re.search(r'<body\b', document, re.I):
        start = re.search(r'<main\b', document, re.I)
        if not start:
            raise ValueError(f'No content entry point: {page_path}')
        head, content = document[:start.start()], document[start.start():]
        if not re.search(r'<head\b', head, re.I):
            head = re.sub(r'(<html\b[^>]*>)', r'\1<head>', head, count=1, flags=re.I)
        if '</head>' not in head.lower():
            head += '</head>'
        content = re.sub(r'</html>\s*$', '', content, flags=re.I)
        document = head + '<body>' + content + '</body></html>\n'
    assets = (f'<meta name="gridline-version" content="{VERSION}">\n'
              f'<link rel="stylesheet" href="{prefix}gridline/gridline.css?v={VERSION}">\n'
              f'<link rel="stylesheet" href="{prefix}gridline/legacy.css?v={VERSION}">\n'
              f'<link rel="stylesheet" href="{prefix}gridline/responsive.css?v={VERSION}">\n'
              f'<link rel="stylesheet" href="{prefix}gridline/interaction.css?v={VERSION}">\n'
              f'<link rel="stylesheet" href="{prefix}gridline/themes.css?v={VERSION}">\n'
              f'<link rel="icon" type="image/svg+xml" href="{prefix}gridline/logo.svg">\n')
    document = re.sub(r'</head>', assets + '</head>', document, count=1, flags=re.I)
    document = re.sub(r'(<meta\b[^>]*name=["\']theme-color["\'][^>]*content=["\'])[^"\']+', r'\g<1>#0000A8', document, flags=re.I)
    outline = []
    def heading(match):
        attrs, content = match.group(1), match.group(2)
        title = unescape(re.sub(r'<[^>]+>', '', content)).strip()
        ident = re.search(r'\bid=["\']([^"\']+)', attrs)
        if ident:
            ident = ident.group(1)
        else:
            ident = 'gl-section-' + str(len(outline) + 1)
            attrs += f' id="{ident}"'
        outline.append((ident, title))
        return f'<h2{attrs}>{content}</h2>'
    # Protect script/style payloads from heading processing, including HTML strings.
    pieces = re.split(r'(<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>)', document, flags=re.I | re.S)
    document = ''.join(piece if index % 2 else re.sub(r'<h2\b([^>]*)>(.*?)</h2>', heading, piece, flags=re.I | re.S) for index, piece in enumerate(pieces))
    chrome = (f'<a class="gl-skip" href="#gl-content">Skip to content</a>'
              f'<div class="gl-global-header" role="banner"><a href="https://thereprocase.github.io/">'
              f'<img src="{prefix}gridline/logo-white.svg" width="20" height="20" alt="">thereprocase</a><span>{escape(label)}</span></div>'
              '<nav class="gl-global-menu" aria-label="Project network">'
              '<a href="https://thereprocase.github.io/">All projects</a>'
              f'<a href="{prefix}index.html" aria-current="true">Project home</a>'
              '<a href="https://thereprocase.github.io/#render-library">Renders</a>'
              '<a href="https://thereprocase.github.io/#airflow">Flow videos</a>'
              f'<a href="https://github.com/thereprocase/{escape(site)}">Source ↗</a></nav>')
    chrome += project_identity(site)
    if outline:
        chrome += '<nav class="gl-outline" aria-label="On this page"><span>CONTENTS</span>' + ''.join(f'<a href="#{escape(ident)}">{escape(title)}</a>' for ident, title in outline[:10]) + '</nav>'
    def body(match):
        attrs = match.group(1)
        if re.search(r'\bclass=', attrs):
            attrs = re.sub(r'(\bclass=["\'])', rf'\1gridline {kind} ', attrs, count=1)
        else:
            attrs += f' class="gridline {kind}"'
        return f'<body{attrs} data-gridline="{VERSION}" data-project="{escape(site)}">' + chrome + '<span id="gl-content" tabindex="-1"></span>'
    document = re.sub(r'<body\b([^>]*)>', body, document, count=1, flags=re.I)
    footer = (f'<div class="gl-global-footer" role="contentinfo"><span>{escape(site.upper())}</span>'
              '<span>GRIDLINE / PROJECT RECORD</span>'
              '<a href="https://thereprocase.github.io/">Open project directory ↗</a></div>')
    return re.sub(r'</body>', footer + '</body>', document, count=1, flags=re.I)
