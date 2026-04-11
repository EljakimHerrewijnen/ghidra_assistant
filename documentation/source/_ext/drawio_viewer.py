from __future__ import annotations

import posixpath
from pathlib import Path
from typing import Any, Dict, List

from docutils import nodes
from docutils.nodes import Element, Node
from docutils.parsers.rst import directives
from sphinx.application import Sphinx
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.util.docutils import SphinxDirective
from sphinx.util.fileutil import copy_asset


class drawio_viewer(nodes.General, nodes.Element):
    pass


def _length_or_percentage(argument: str) -> str:
    value = argument.strip()
    if not value:
        raise ValueError('height must not be empty')
    return value


class DrawioViewerDirective(SphinxDirective):
    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'height': _length_or_percentage,
    }

    def run(self) -> List[Node]:
        rel_filename, abs_filename = self.env.relfn2path(self.arguments[0])
        self.env.note_dependency(abs_filename)

        viewer_node = drawio_viewer()
        viewer_node['source_uri'] = rel_filename.replace('\\', '/')
        viewer_node['height'] = self.options.get('height', '420px')

        assets = getattr(self.env, 'drawio_viewer_assets', set())
        assets.add(rel_filename.replace('\\', '/'))
        self.env.drawio_viewer_assets = assets
        return [viewer_node]


def visit_drawio_viewer_html(translator, node: drawio_viewer) -> None:
    builder = translator.builder
    current_uri = builder.get_target_uri(builder.current_docname)
    current_dir = posixpath.dirname(current_uri)
    asset_uri = posixpath.join('_drawio', node['source_uri'])
    relative_asset_uri = posixpath.relpath(asset_uri, current_dir or '.')

    translator.body.append(
        '<div class="drawio-viewer" '
        f'data-drawio-src="{relative_asset_uri}" '
        f'data-drawio-height="{node["height"]}">'
        '<div class="drawio-viewer__loading">Loading diagram…</div>'
        '<iframe class="drawio-viewer__frame" loading="lazy" referrerpolicy="no-referrer"></iframe>'
        '<noscript><p>JavaScript is required to render this DrawIO diagram in the page.</p></noscript>'
        '</div>'
    )
    raise nodes.SkipNode


def depart_drawio_viewer_html(translator, node: drawio_viewer) -> None:
    return None


def copy_drawio_assets(app: Sphinx, exc: Exception | None) -> None:
    if exc is not None or not isinstance(app.builder, StandaloneHTMLBuilder):
        return

    env = app.builder.env
    for rel_path in sorted(getattr(env, 'drawio_viewer_assets', set())):
        src = Path(app.srcdir) / rel_path
        dst = Path(app.outdir) / '_drawio' / rel_path
        copy_asset(str(src), str(dst.parent))


def setup(app: Sphinx) -> Dict[str, Any]:
    app.add_node(
        drawio_viewer,
        html=(visit_drawio_viewer_html, depart_drawio_viewer_html),
    )
    app.add_directive('drawio-viewer', DrawioViewerDirective)
    app.add_css_file('drawio-viewer.css')
    app.add_js_file('drawio-viewer.js', loading_method='defer')
    app.connect('build-finished', copy_drawio_assets)
    return {'version': '0.1', 'parallel_read_safe': True}