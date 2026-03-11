"""Demo application for cjm-fasthtml-virtual-collection library.

Showcases virtualized collection rendering with a 500-item table using
CSS table display, overflow-based auto-fit, and display:contents slots.

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
    from fasthtml.common import fast_app, Div, H1, H2, P, A, Script, APIRouter

    from cjm_fasthtml_daisyui.core.resources import get_daisyui_headers
    from cjm_fasthtml_daisyui.core.testing import create_theme_persistence_script
    from cjm_fasthtml_daisyui.utilities.semantic_colors import text_dui
    from cjm_fasthtml_daisyui.components.actions.button import btn, btn_colors, btn_sizes

    from cjm_fasthtml_tailwind.utilities.spacing import p, m
    from cjm_fasthtml_tailwind.utilities.sizing import container, max_w
    from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight, text_align
    from cjm_fasthtml_tailwind.core.base import combine_classes

    from cjm_fasthtml_app_core.components.navbar import create_navbar
    from cjm_fasthtml_app_core.core.routing import register_routes
    from cjm_fasthtml_app_core.core.htmx import handle_htmx_request
    from cjm_fasthtml_app_core.core.layout import wrap_with_layout

    from cjm_fasthtml_keyboard_navigation.core.manager import ZoneManager
    from cjm_fasthtml_keyboard_navigation.components.system import render_keyboard_system

    from cjm_fasthtml_virtual_collection.core.models import (
        VirtualCollectionConfig, VirtualCollectionState, ColumnDef,
    )
    from cjm_fasthtml_virtual_collection.core.html_ids import VirtualCollectionHtmlIds
    from cjm_fasthtml_virtual_collection.core.button_ids import VirtualCollectionButtonIds
    from cjm_fasthtml_virtual_collection.components.collection import render_virtual_collection
    from cjm_fasthtml_virtual_collection.routes.router import init_virtual_collection_router
    from cjm_fasthtml_virtual_collection.keyboard.actions import (
        create_collection_focus_zone, create_collection_nav_actions,
        build_collection_url_map, apply_nav_sync,
    )
    from cjm_fasthtml_virtual_collection.js.scroll import generate_scroll_nav_js
    from cjm_fasthtml_virtual_collection.js.touch import generate_touch_nav_js
    from cjm_fasthtml_virtual_collection.js.scrollbar import generate_scrollbar_js
    from cjm_fasthtml_virtual_collection.js.auto_fit import generate_auto_fit_js, auto_fit_callback_name

    from cjm_fasthtml_viewport_fit.models import ViewportFitConfig
    from cjm_fasthtml_viewport_fit.components import render_viewport_fit_script

    print("\n" + "=" * 70)
    print("Initializing cjm-fasthtml-virtual-collection Demo")
    print("=" * 70)

    # Create FastHTML app
    app, rt = fast_app(
        pico=False,
        hdrs=[
            *get_daisyui_headers(),
            create_theme_persistence_script(),
        ],
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
        columns=(
            ColumnDef(key="select", header=""),
            ColumnDef(key="name", header="Name", sortable=True),
            ColumnDef(key="size", header="Size", sortable=True),
            ColumnDef(key="modified", header="Modified", sortable=True),
            ColumnDef(key="type", header="Type"),
        ),
    )

    # Start with 1 visible row — auto-fit grows from there
    state = VirtualCollectionState(
        total_items=len(items),
        visible_rows=1,
        cursor_index=0,
    )

    ids = VirtualCollectionHtmlIds(prefix=config.prefix)
    btn_ids = VirtualCollectionButtonIds(prefix=config.prefix)

    print(f"  Sample data: {len(items):,} items")
    print(f"  Config: prefix={config.prefix}, columns={len(config.columns)}")

    # -------------------------------------------------------------------------
    # Cell render callback
    # -------------------------------------------------------------------------

    def _format_size(size_bytes: int) -> str:
        """Format file size for display."""
        if size_bytes < 1024: return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024: return f"{size_bytes / 1024:.1f} KB"
        else: return f"{size_bytes / (1024 * 1024):.1f} MB"

    def render_cell(item, ctx):
        """Render a table cell based on column key."""
        from fasthtml.common import Span, Input
        from cjm_fasthtml_daisyui.components.data_display.badge import badge, badge_styles
        from cjm_fasthtml_daisyui.components.data_input.checkbox import checkbox, checkbox_sizes
        if ctx.column.key == "select":
            return Input(
                type="checkbox", checked=item.selected,
                cls=combine_classes(checkbox, checkbox_sizes.sm),
                hx_post=f"/select?row_index={ctx.row_index}",
                hx_swap="none",
            )
        elif ctx.column.key == "name":
            return Span(item.name)
        elif ctx.column.key == "size":
            return Span(_format_size(item.size_bytes))
        elif ctx.column.key == "modified":
            return Span(item.modified)
        elif ctx.column.key == "type":
            return Span(item.file_type, cls=combine_classes(badge, badge_styles.ghost))
        return Span("")

    # -------------------------------------------------------------------------
    # Collection router (Tier 2 — auto-wires nav routes)
    # -------------------------------------------------------------------------

    from cjm_fasthtml_virtual_collection.components.table import render_cell_oob

    def on_activate(item, row_index, st):
        """Toggle selection on the focused row via Space/Enter."""
        item.selected = not item.selected
        select_col = config.columns[0]  # "select" column
        return render_cell_oob(
            item, select_col, row_index,
            st.total_items, ids, render_cell,
        )

    def sort_items(items_list, column_key, ascending):
        """Sort items in place by column key."""
        key_map = {
            "name": lambda x: x.name,
            "size": lambda x: x.size_bytes,
            "modified": lambda x: x.modified,
            "type": lambda x: x.file_type,
        }
        key_fn = key_map.get(column_key)
        if key_fn:
            items_list.sort(key=key_fn, reverse=not ascending)

    vc_router, urls = init_virtual_collection_router(
        config=config,
        state_getter=lambda: state,
        state_setter=lambda s: None,  # In-memory state, no persistence needed
        get_items=lambda: items,
        render_cell=render_cell,
        on_activate=on_activate,
        sort_callback=sort_items,
        route_prefix="/vc",
    )

    print(f"  Collection router: /vc")
    print(f"  URLs: nav_up={urls.nav_up}, nav_down={urls.nav_down}")

    # -------------------------------------------------------------------------
    # Click-to-select route (cell-level OOB demo)
    # -------------------------------------------------------------------------

    from cjm_fasthtml_virtual_collection.routes.handlers import build_cursor_move_response

    @router
    def select(row_index: int):
        """Toggle selection and move cursor — checkbox OOB + focus jump in one response."""
        items[row_index].selected = not items[row_index].selected
        select_col = config.columns[0]  # "select" column

        # Checkbox cell OOB
        cell_oob = render_cell_oob(
            items[row_index], select_col, row_index,
            state.total_items, ids, render_cell,
        )

        # Move cursor to clicked row
        old_cursor = state.cursor_index
        state.cursor_index = row_index
        cursor_oobs = build_cursor_move_response(
            old_cursor, items, state, config, ids, render_cell,
            focus_url=urls.focus_row,
        )

        return (cell_oob,) + cursor_oobs

    print(f"  Select route: /select")

    # -------------------------------------------------------------------------
    # Keyboard system
    # -------------------------------------------------------------------------

    zone = create_collection_focus_zone(ids)
    nav_actions = create_collection_nav_actions(zone.id, btn_ids)
    manager = ZoneManager(zones=(zone,), actions=nav_actions)

    url_map = build_collection_url_map(btn_ids, urls)
    target_map = {btn_id: f"#{ids.rows}" for btn_id in url_map}
    swap_map = {btn_id: "none" for btn_id in url_map}

    kb_system = render_keyboard_system(
        manager,
        url_map=url_map,
        target_map=target_map,
        swap_map=swap_map,
    )

    apply_nav_sync(kb_system, ids)

    # Scroll wheel JS + scrollbar JS (static — don't depend on state)
    scroll_js = generate_scroll_nav_js(ids, btn_ids)
    touch_js = generate_touch_nav_js(ids, btn_ids, urls)
    scrollbar_js = generate_scrollbar_js(ids, urls)

    # Viewport-fit config — target wrapper, trigger auto-fit on resize
    vf_config = ViewportFitConfig(
        namespace=config.prefix,
        target_id=ids.wrapper,
        resize_callback=auto_fit_callback_name(config),
        enable_htmx_settle=False,  # Auto-fit handles settle events itself
        debug=False,
    )

    print(f"  Keyboard system: {len(nav_actions)} actions, {len(url_map)} buttons")
    print(f"  Viewport-fit: target={ids.wrapper}, auto-fit callback={auto_fit_callback_name(config)}")

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

                P("Virtualized collection rendering with CSS table display, "
                  "overflow-based auto-fit, and cell-level HTMX updates.",
                  cls=combine_classes(font_size.lg, text_dui.base_content, m.b(6))),

                Div(
                    H2("Features", cls=combine_classes(font_size._2xl, font_weight.bold, m.b(4))),
                    Div(
                        P("CSS table display with automatic column width coordination", cls=m.b(2)),
                        P("Overflow-based auto-fit (no fixed row height)", cls=m.b(2)),
                        P("display:contents slots for OOB navigation", cls=m.b(2)),
                        P("Custom scrollbar with drag-to-jump", cls=m.b(2)),
                        P("Cell-level OOB HTMX updates", cls=m.b(2)),
                        P("Keyboard, wheel, and touch navigation", cls=m.b(2)),
                        cls=combine_classes(text_align.left, max_w.md, m.x.auto, m.b(8))
                    ),
                ),

                A("Open Table Demo",
                  href=demo_table.to(),
                  cls=combine_classes(btn, btn_colors.primary, btn_sizes.lg)),

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
        """Table demo page — shows virtual collection with keyboard + wheel navigation."""

        def table_content():
            # Auto-fit JS generated at render time to capture current visible_rows
            auto_fit_js = generate_auto_fit_js(
                ids, config, urls,
                total_items=len(items),
                initial_visible=state.visible_rows,
            )

            return Div(
                H2("Table Demo",
                   cls=combine_classes(font_size._2xl, font_weight.bold, m.b(4))),
                P(f"{state.total_items:,} items · Overflow-based auto-fit · "
                  f"Arrow keys / PageUp / PageDown / Home / End / Mouse wheel",
                  cls=combine_classes(text_dui.base_content, m.b(4))),

                # Virtual collection table
                render_virtual_collection(
                    items=items, config=config, state=state,
                    ids=ids, urls=urls, render_cell=render_cell,
                ),

                # Keyboard system components
                kb_system.script,
                kb_system.hidden_inputs,
                kb_system.action_buttons,

                # Scroll wheel + scrollbar + auto-fit + viewport-fit JS
                Script(scroll_js),
                Script(touch_js),
                Script(scrollbar_js),
                Script(auto_fit_js),
                render_viewport_fit_script(vf_config),

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

    register_routes(app, router, vc_router)

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
