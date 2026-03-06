"""Demo application for cjm-fasthtml-virtual-collection library.

Showcases virtualized collection rendering with a 500-item table.

Run with: python demo_app.py
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import random


# =============================================================================
# Configuration
# =============================================================================

DEMO_PORT = 5033
ITEM_COUNT = 500


# =============================================================================
# Sample Data
# =============================================================================

@dataclass
class SampleFile:
    """Sample file item for demo."""
    name: str
    size_bytes: int
    modified: str
    file_type: str
    selected: bool = False


def _generate_sample_data(count: int = 500) -> list[SampleFile]:
    """Generate sample file data."""
    extensions = ['.txt', '.py', '.md', '.json', '.csv', '.log', '.yaml', '.toml']
    types = ['document', 'code', 'data', 'config']
    base_date = datetime(2026, 1, 1)
    items = []
    for i in range(count):
        ext = extensions[i % len(extensions)]
        items.append(SampleFile(
            name=f"file_{i:04d}{ext}",
            size_bytes=random.randint(100, 10_000_000),
            modified=(base_date + timedelta(days=i % 365)).strftime("%Y-%m-%d"),
            file_type=types[i % len(types)],
        ))
    return items


# =============================================================================
# Demo Application
# =============================================================================

def main():
    """Initialize virtual collection demo and start the server."""
    from fasthtml.common import fast_app, Div, H1, H2, P, Li, Ul, Hr, A, APIRouter

    from cjm_fasthtml_daisyui.core.resources import get_daisyui_headers
    from cjm_fasthtml_daisyui.core.testing import create_theme_persistence_script
    from cjm_fasthtml_daisyui.utilities.semantic_colors import text_dui

    from cjm_fasthtml_tailwind.utilities.spacing import p, m
    from cjm_fasthtml_tailwind.utilities.sizing import container, max_w
    from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight, text_align
    from cjm_fasthtml_tailwind.core.base import combine_classes

    from cjm_fasthtml_app_core.components.navbar import create_navbar
    from cjm_fasthtml_app_core.core.routing import register_routes
    from cjm_fasthtml_app_core.core.htmx import handle_htmx_request
    from cjm_fasthtml_app_core.core.layout import wrap_with_layout

    from cjm_fasthtml_virtual_collection.core.models import (
        VirtualCollectionConfig, VirtualCollectionState,
        ColumnDef, VirtualCollectionUrls,
    )
    from cjm_fasthtml_virtual_collection.core.html_ids import VirtualCollectionHtmlIds
    from cjm_fasthtml_virtual_collection.core.button_ids import VirtualCollectionButtonIds
    from cjm_fasthtml_virtual_collection.core.windowing import compute_window

    print("\n" + "=" * 70)
    print("Initializing cjm-fasthtml-virtual-collection Demo")
    print("=" * 70)

    # Create FastHTML app
    app, rt = fast_app(
        pico=False,
        hdrs=[*get_daisyui_headers(), create_theme_persistence_script()],
        title="Virtual Collection Demo",
        htmlkw={'data-theme': 'light'},
        secret_key="demo-secret-key"
    )

    router = APIRouter(prefix="")

    print("  FastHTML app created")

    # -------------------------------------------------------------------------
    # Sample data and collection state
    # -------------------------------------------------------------------------

    items = _generate_sample_data(ITEM_COUNT)

    config = VirtualCollectionConfig(
        prefix="demo",
        layout="table",
        row_height=40,
        columns=(
            ColumnDef(key="select", header="", width="40px"),
            ColumnDef(key="name", header="Name", width="1fr", sortable=True),
            ColumnDef(key="size", header="Size", width="100px", sortable=True),
            ColumnDef(key="modified", header="Modified", width="120px", sortable=True),
            ColumnDef(key="type", header="Type", width="80px"),
        ),
    )

    state = VirtualCollectionState(
        total_items=len(items),
        visible_rows=15,
    )

    ids = VirtualCollectionHtmlIds(prefix=config.prefix)
    btn_ids = VirtualCollectionButtonIds(prefix=config.prefix)
    urls = VirtualCollectionUrls()

    print(f"  Sample data: {len(items):,} items")
    print(f"  Config: prefix={config.prefix}, columns={len(config.columns)}")

    # -------------------------------------------------------------------------
    # Page routes
    # -------------------------------------------------------------------------

    @router
    def index(request):
        """Homepage with demo overview."""

        def home_content():
            return Div(
                H1("Virtual Collection Demo",
                   cls=combine_classes(font_size._4xl, font_weight.bold, m.b(4))),

                P("Virtualized collection rendering with discrete navigation, "
                  "custom scrollbar, and cell-level HTMX updates.",
                  cls=combine_classes(font_size.lg, text_dui.base_content, m.b(6))),

                Div(
                    H2("Features", cls=combine_classes(font_size._2xl, font_weight.bold, m.b(4))),
                    Div(
                        P("Discrete navigation (card-stack approach)", cls=m.b(2)),
                        P("Custom scrollbar with drag-to-jump", cls=m.b(2)),
                        P("Cell-level OOB HTMX updates", cls=m.b(2)),
                        P("Auto-fit visible rows from viewport height", cls=m.b(2)),
                        P("Sortable columns", cls=m.b(2)),
                        cls=combine_classes(text_align.left, max_w.md, m.x.auto, m.b(8))
                    ),
                ),

                A("Open Table Demo",
                  href=demo_table.to(),
                  cls="btn btn-primary btn-lg"),

                cls=combine_classes(
                    container, max_w._4xl, m.x.auto, p(8), text_align.center
                )
            )

        return handle_htmx_request(
            request, home_content,
            wrap_fn=lambda content: wrap_with_layout(content, navbar=navbar)
        )

    @router
    def demo_table(request):
        """Table demo page — shows virtual collection with sample file data."""

        def table_content():
            # Placeholder until rendering components are built (Phase 2)
            window_start, window_end = compute_window(
                state.window_start, state.visible_rows, state.total_items
            )
            rows_info = [
                Li(f"{items[i].name} — {items[i].size_bytes:,} bytes — {items[i].modified}")
                for i in range(window_start, window_end)
            ]
            return Div(
                H2("Table Demo",
                   cls=combine_classes(font_size._2xl, font_weight.bold, m.b(4))),
                P(f"Total items: {state.total_items} | "
                  f"Visible rows: {state.visible_rows} | "
                  f"Window: rows {window_start}-{window_end - 1}",
                  cls=combine_classes(text_dui.base_content, m.b(4))),
                P(f"Columns: {', '.join(c.key for c in config.columns)}",
                  cls=combine_classes(text_dui.base_content, m.b(4))),
                Hr(),
                Ul(*rows_info),
                cls=combine_classes(container, max_w._5xl, m.x.auto, p(4))
            )

        return handle_htmx_request(
            request, table_content,
            wrap_fn=lambda content: wrap_with_layout(content, navbar=navbar)
        )

    # -------------------------------------------------------------------------
    # Navbar and route registration
    # -------------------------------------------------------------------------

    navbar = create_navbar(
        title="Virtual Collection Demo",
        nav_items=[
            ("Home", index),
            ("Table", demo_table),
        ],
        home_route=index,
        theme_selector=True
    )

    register_routes(app, router)

    # Debug output
    print("\n" + "=" * 70)
    print("Registered Routes:")
    print("=" * 70)
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"  {route.path}")
    print("=" * 70)
    print("Demo App Ready!")
    print("=" * 70 + "\n")

    return app


if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading

    app = main()

    port = DEMO_PORT
    host = "0.0.0.0"
    display_host = 'localhost' if host in ['0.0.0.0', '127.0.0.1'] else host

    print(f"Server: http://{display_host}:{port}")
    print(f"\n  http://{display_host}:{port}/              — Homepage")
    print(f"  http://{display_host}:{port}/demo_table    — Table demo")
    print()

    timer = threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}"))
    timer.daemon = True
    timer.start()

    uvicorn.run(app, host=host, port=port)
