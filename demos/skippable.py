"""Skippable items demo — tests cursor navigation that skips non-focusable rows.

Simulates a grouped list where category headers are interspersed with data rows.
Headers are skippable (cursor never lands on them). Arrow keys, Page Up/Down,
Home/End, and click-to-focus all skip header rows.

Edge cases to test:
- Navigate up from first data row: window scrolls to reveal leading headers
- Navigate down past last data row: window scrolls to reveal trailing headers
- Cursor off-screen after resize: next keystroke scrolls to bring cursor into view

The header row rendering tests the "refined option (a)" approach:
render group content in the first cell, hide remaining cells so
the first cell expands to fill the row width.
"""

from dataclasses import dataclass

from fasthtml.common import Div, H2, P, Span, Button, Script

from cjm_fasthtml_daisyui.utilities.semantic_colors import bg_dui, text_dui, border_dui
from cjm_fasthtml_daisyui.components.data_display.badge import badge, badge_colors
from cjm_fasthtml_daisyui.components.actions.button import btn, btn_styles, btn_sizes

from cjm_fasthtml_tailwind.utilities.spacing import p, m
from cjm_fasthtml_tailwind.utilities.sizing import w, h
from cjm_fasthtml_tailwind.utilities.typography import (
    font_size, font_weight, truncate, uppercase, tracking,
)
from cjm_fasthtml_tailwind.utilities.flexbox_and_grid import (
    flex_display, flex_direction, items as align_items, gap, grow, justify,
)
from cjm_fasthtml_tailwind.utilities.borders import border, rounded
from cjm_fasthtml_tailwind.utilities.layout import overflow
from cjm_fasthtml_tailwind.core.base import combine_classes

from cjm_fasthtml_virtual_collection.core.models import (
    VirtualCollectionConfig, VirtualCollectionState, ColumnDef, VirtualCollectionUrls,
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

from cjm_fasthtml_keyboard_navigation.core.manager import ZoneManager
from cjm_fasthtml_keyboard_navigation.components.system import render_keyboard_system

from cjm_fasthtml_viewport_fit.models import ViewportFitConfig
from cjm_fasthtml_viewport_fit.components import render_viewport_fit_script


# =============================================================================
# Sample data — grouped items with category headers
# =============================================================================

@dataclass
class SkipItem:
    """Item that can be either a category header or a data row."""
    item_type: str   # "header" or "record"
    name: str = ""
    category: str = ""
    value: str = ""
    group_count: int = 0


def _generate_grouped_items() -> list[SkipItem]:
    """Generate items with category headers interspersed."""
    categories = [
        ("Documents", [
            ("report.pdf", "2.1 MB"), ("notes.txt", "12 KB"), ("readme.md", "4 KB"),
            ("manual.pdf", "8.5 MB"), ("changelog.md", "1 KB"), ("license.txt", "2 KB"),
        ]),
        ("Code", [
            ("app.py", "8 KB"), ("utils.py", "3 KB"), ("test_app.py", "5 KB"),
            ("config.yaml", "1 KB"), ("setup.py", "2 KB"), ("models.py", "12 KB"),
            ("routes.py", "6 KB"), ("helpers.py", "4 KB"),
        ]),
        ("Data", [
            ("dataset.csv", "45 MB"), ("results.json", "128 KB"), ("cache.db", "12 MB"),
            ("metrics.parquet", "890 KB"), ("index.sqlite", "3 MB"),
        ]),
        ("Images", [
            ("photo.jpg", "3.2 MB"), ("diagram.png", "890 KB"),
            ("icon.svg", "4 KB"), ("banner.webp", "156 KB"),
            ("screenshot.png", "1.5 MB"), ("logo.svg", "8 KB"),
            ("thumbnail.jpg", "45 KB"), ("background.webp", "2.1 MB"),
        ]),
        ("Audio", [
            ("episode_01.mp3", "45 MB"), ("episode_02.mp3", "52 MB"),
            ("interview.wav", "180 MB"), ("music.flac", "32 MB"),
            ("voiceover.ogg", "8 MB"), ("podcast_final.mp3", "67 MB"),
        ]),
        ("Logs", [
            ("app.log", "12 MB"), ("error.log", "2.3 MB"), ("access.log", "8 MB"),
            ("debug.log", "45 MB"), ("audit.log", "1.2 MB"),
        ]),
        ("Config", [
            ("settings.toml", "1 KB"), (".env", "512 B"), ("docker-compose.yml", "3 KB"),
            ("nginx.conf", "2 KB"), ("supervisord.conf", "1 KB"),
        ]),
        ("Archives", [
            ("backup.tar.gz", "1.2 GB"), ("release.zip", "45 MB"),
            ("data_2025.tar.gz", "890 MB"), ("old_backup.zip", "234 MB"),
            ("source_code.tar.xz", "12 MB"), ("assets.zip", "567 MB"),
        ]),
        ("Videos", [
            ("tutorial.mp4", "1.8 GB"), ("demo.webm", "234 MB"),
            ("recording.mkv", "3.4 GB"), ("clip.mp4", "89 MB"),
        ]),
        ("Scripts", [
            ("deploy.sh", "3 KB"), ("backup.sh", "2 KB"), ("migrate.py", "5 KB"),
            ("cleanup.sh", "1 KB"), ("init_db.sql", "8 KB"), ("seed.py", "4 KB"),
            ("test_all.sh", "1 KB"),
        ]),
    ]
    result = []
    for cat_name, files in categories:
        result.append(SkipItem(
            item_type="header", name=cat_name,
            category=cat_name, group_count=len(files),
        ))
        for fname, fsize in files:
            result.append(SkipItem(
                item_type="record", name=fname,
                category=cat_name, value=fsize,
            ))
    return result


# =============================================================================
# Demo setup
# =============================================================================

def setup():
    """Set up the skippable items demo."""
    items = _generate_grouped_items()

    config = VirtualCollectionConfig(
        prefix="sk",
        layout="table",
        columns=(
            ColumnDef(key="name", header="Name", sortable=False),
            ColumnDef(key="value", header="Size"),
            ColumnDef(key="category", header="Category"),
        ),
    )
    state = VirtualCollectionState(
        total_items=len(items), visible_rows=1, cursor_index=1,  # Start on first data row (skip header at 0)
    )
    ids = VirtualCollectionHtmlIds(prefix=config.prefix)
    btn_ids = VirtualCollectionButtonIds(prefix=config.prefix)

    # Detail panel for on_cursor_change demo
    detail_panel_id = "sk-detail-panel"

    def _render_detail(item, index):
        """Render detail panel content for the focused item."""
        return Div(
            Span(f"Focused: ", cls=font_weight.semibold),
            Span(item.name, cls=combine_classes(font_weight.bold, text_dui.primary)),
            Span(f" ({item.value})", cls=text_dui.base_content.opacity(70)) if item.value else None,
            Span(f" — row {index} of {len(items)}", cls=combine_classes(font_size.sm, text_dui.base_content.opacity(50))),
            id=detail_panel_id,
            hx_swap_oob="innerHTML",
            cls=combine_classes(p(3), bg_dui.base_200, rounded(), font_size.sm),
        )

    def render_cell(item, ctx):
        """Render cell based on item type and column key."""
        if item.item_type == "header":
            # Header rows: render content only in first column, hide other cells
            if ctx.column.key == config.columns[0].key:
                return Div(
                    Span(item.name, cls=combine_classes(
                        font_weight.bold, uppercase, tracking.wide, font_size.xs,
                    )),
                    Span(
                        f"{item.group_count} items",
                        cls=combine_classes(badge, badge_colors.neutral, font_size.xs, m.l(2)),
                    ),
                    cls=combine_classes(flex_display, align_items.center, gap(2), w.full),
                )
            else:
                # Hidden cells — display:none so first cell fills the row
                return Div(style="display:none")

        # Data rows: normal cell rendering
        if ctx.column.key == "name":
            return Span(item.name, cls=str(truncate))
        elif ctx.column.key == "value":
            return Span(item.value, cls=combine_classes(text_dui.base_content.opacity(70), font_size.sm))
        elif ctx.column.key == "category":
            return Span(item.category, cls=combine_classes(text_dui.base_content.opacity(50), font_size.sm))
        return Span("")

    def is_item_skippable(item):
        """Header items are skippable — cursor never lands on them."""
        return item.item_type == "header"

    def on_cursor_change(item, cursor_index, st):
        """Update detail panel when cursor changes."""
        return (_render_detail(item, cursor_index),)

    vc_router, urls = init_virtual_collection_router(
        config=config,
        state_getter=lambda: state,
        state_setter=lambda s: None,
        get_items=lambda: items,
        render_cell=render_cell,
        is_skippable=is_item_skippable,
        on_cursor_change=on_cursor_change,
        route_prefix="/sk",
    )

    # Keyboard system
    zone = create_collection_focus_zone(ids)
    nav_actions = create_collection_nav_actions(zone.id, btn_ids)
    manager = ZoneManager(zones=(zone,), actions=nav_actions)
    url_map = build_collection_url_map(btn_ids, urls)
    target_map = {bid: f"#{ids.rows}" for bid in url_map}
    swap_map = {bid: "none" for bid in url_map}
    kb_system = render_keyboard_system(manager, url_map=url_map, target_map=target_map, swap_map=swap_map)
    apply_nav_sync(kb_system, ids)

    # Static JS
    scroll_js = generate_scroll_nav_js(ids, btn_ids)
    touch_js = generate_touch_nav_js(ids, btn_ids, urls)
    scrollbar_js = generate_scrollbar_js(ids, urls)

    vf_config = ViewportFitConfig(
        namespace=config.prefix,
        target_id=ids.wrapper,
        resize_callback=auto_fit_callback_name(config),
        enable_htmx_settle=False,
    )

    header_count = sum(1 for i in items if i.item_type == "header")
    data_count = len(items) - header_count

    def page_content():
        auto_fit_js = generate_auto_fit_js(
            ids, config, urls,
            total_items=len(items),
            initial_visible=state.visible_rows,
        )

        return Div(
            # Description
            Div(
                H2("Skippable Items",
                   cls=combine_classes(font_size._2xl, font_weight.bold)),
                P(f"{len(items)} total items ({header_count} category headers + {data_count} data rows). "
                  f"Headers are skippable — cursor skips over them. "
                  f"Arrow keys, Page Up/Down, Home/End, and click all skip headers.",
                  cls=combine_classes(text_dui.base_content, font_size.sm, m.t(1))),
                cls=combine_classes(m.b(4))
            ),

            # Detail panel (updated via on_cursor_change)
            Div(
                Span("No item focused"),
                id=detail_panel_id,
                cls=combine_classes(p(3), bg_dui.base_200, rounded(), font_size.sm, m.b(4)),
            ),

            # Virtual collection
            render_virtual_collection(
                items=items, config=config, state=state,
                ids=ids, urls=urls, render_cell=render_cell,
            ),

            # Keyboard + JS
            kb_system.script,
            kb_system.hidden_inputs,
            kb_system.action_buttons,
            Script(scroll_js),
            Script(touch_js),
            Script(scrollbar_js),
            Script(auto_fit_js),
            render_viewport_fit_script(vf_config),

            cls=combine_classes(p(4)),
        )

    return dict(
        router=vc_router,
        page_content=page_content,
        title="Skippable Items",
        description="Category headers are skippable — cursor skips over them during navigation.",
        badges=[
            ("is_skippable", badge_colors.primary),
            ("on_cursor_change", badge_colors.secondary),
            ("group headers", badge_colors.accent),
        ],
    )
