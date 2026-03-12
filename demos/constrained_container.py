"""Constrained container demo — tests virtual collection inside a fixed-height parent.

Simulates the file browser use case where the collection must fit within a
fixed-height container (h-96 = 384px) with siblings (header bar) above it.

Height chain under test:
    div.h-96 (fixed 384px)
      └── div.flex.flex-col.h-full (fills parent)
            ├── div (header bar, ~40px)
            └── div.flex.flex-col.grow.overflow-hidden (content wrapper)
                  └── render_virtual_collection() (must fill, not exceed)
                        ├── wrapper (viewport-fit target)
                        ├── footer
                        └── hidden input
"""

from dataclasses import dataclass

from fasthtml.common import Div, H2, P, Span, Script

from cjm_fasthtml_daisyui.utilities.semantic_colors import bg_dui, text_dui, border_dui
from cjm_fasthtml_daisyui.components.data_display.badge import badge, badge_colors

from cjm_fasthtml_tailwind.utilities.spacing import p, m
from cjm_fasthtml_tailwind.utilities.sizing import w, h
from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight, truncate
from cjm_fasthtml_tailwind.utilities.flexbox_and_grid import (
    flex_display, flex_direction, items, gap, grow,
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
# Sample data
# =============================================================================

ITEM_COUNT = 200

@dataclass
class SampleFile:
    name: str
    size: str
    file_type: str


def _generate_items(count: int) -> list[SampleFile]:
    extensions = ['.txt', '.py', '.md', '.json', '.csv']
    types = ['document', 'code', 'data', 'config', 'log']
    return [
        SampleFile(
            name=f"file_{i:04d}{extensions[i % len(extensions)]}",
            size=f"{(i * 137 + 42) % 9999} KB",
            file_type=types[i % len(types)],
        )
        for i in range(count)
    ]


# =============================================================================
# Demo setup
# =============================================================================

def setup():
    """Set up the constrained container demo."""
    items = _generate_items(ITEM_COUNT)

    config = VirtualCollectionConfig(
        prefix="cc",
        layout="table",
        columns=(
            ColumnDef(key="name", header="Name", sortable=True),
            ColumnDef(key="size", header="Size", sortable=True),
            ColumnDef(key="type", header="Type"),
        ),
    )
    state = VirtualCollectionState(
        total_items=len(items), visible_rows=1, cursor_index=0,
    )
    ids = VirtualCollectionHtmlIds(prefix=config.prefix)
    btn_ids = VirtualCollectionButtonIds(prefix=config.prefix)

    def render_cell(item, ctx):
        if ctx.column.key == "name":
            return Span(item.name, cls=str(truncate))
        elif ctx.column.key == "size":
            return Span(item.size, cls=combine_classes(text_dui.base_content.opacity(70), font_size.sm))
        elif ctx.column.key == "type":
            return Span(item.file_type, cls=combine_classes(text_dui.base_content.opacity(70), font_size.sm))
        return Span("")

    def sort_items(items_list, column_key, ascending):
        key_map = {"name": lambda x: x.name, "size": lambda x: x.size, "type": lambda x: x.file_type}
        fn = key_map.get(column_key)
        if fn:
            items_list.sort(key=fn, reverse=not ascending)

    vc_router, urls = init_virtual_collection_router(
        config=config,
        state_getter=lambda: state,
        state_setter=lambda s: None,
        get_items=lambda: items,
        render_cell=render_cell,
        sort_callback=sort_items,
        route_prefix="/cc",
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
        container_id="cc-content",
        resize_callback=auto_fit_callback_name(config),
        enable_htmx_settle=False,
        debug=True,
    )

    def page_content():
        auto_fit_js = generate_auto_fit_js(
            ids, config, urls,
            total_items=len(items),
            initial_visible=state.visible_rows,
        )

        return Div(
            # Description
            Div(
                H2("Constrained Container",
                   cls=combine_classes(font_size._2xl, font_weight.bold)),
                P(f"{len(items)} items inside h-96 (384px) container with header sibling. "
                  f"Collection must fill but not exceed the constrained parent.",
                  cls=combine_classes(text_dui.base_content, font_size.sm, m.t(1))),
                cls=combine_classes(m.b(4))
            ),

            # Height diagnostic display
            Div(
                Span("Heights: ", cls=font_weight.semibold),
                Span("", id="cc-heights", cls=text_dui.base_content),
                cls=combine_classes(m.b(4), p(2), bg_dui.base_200, rounded(), font_size.sm),
            ),

            # ---- The constrained container (h-96) ----
            Div(
                # Inner flex column (h-full fills the h-96 parent)
                Div(
                    # Header bar (sibling of collection)
                    Div(
                        Span("Header Bar (sibling)",
                             cls=combine_classes(font_size.sm, font_weight.semibold)),
                        cls=combine_classes(
                            p.x(3), p.y(2), bg_dui.base_200,
                            border.b(), border_dui.base_300,
                        ),
                    ),

                    # Content wrapper (flex col, grow, overflow hidden)
                    Div(
                        render_virtual_collection(
                            items=items, config=config, state=state,
                            ids=ids, urls=urls, render_cell=render_cell,
                        ),
                        id="cc-content",
                        cls=combine_classes(
                            grow(), overflow.hidden,
                            flex_display, flex_direction.col,
                        ),
                    ),

                    cls=combine_classes(
                        flex_display, flex_direction.col,
                        w.full, h.full, overflow.hidden,
                    ),
                ),

                # Outer constrained container
                cls=combine_classes(h(96), border(), rounded.lg, overflow.hidden),
            ),

            # Keyboard + JS (outside the constrained container)
            kb_system.script,
            kb_system.hidden_inputs,
            kb_system.action_buttons,
            Script(scroll_js),
            Script(touch_js),
            Script(scrollbar_js),
            Script(auto_fit_js),
            render_viewport_fit_script(vf_config),

            # Height diagnostic script
            Script(f"""
            (function() {{
                function showHeights() {{
                    const ids = ['cc-content', '{ids.collection}', '{ids.wrapper}'];
                    const parts = [];
                    ids.forEach(function(id) {{
                        const el = document.getElementById(id);
                        if (el) {{
                            parts.push('#' + id + '=' + Math.round(el.getBoundingClientRect().height) + 'px');
                        }}
                    }});
                    const disp = document.getElementById('cc-heights');
                    if (disp) disp.textContent = parts.join(' | ');
                }}
                setInterval(showHeights, 500);
                showHeights();
            }})();
            """),

            cls=combine_classes(p(4)),
        )

    return dict(
        router=vc_router,
        page_content=page_content,
        title="Constrained Container",
        description="Virtual collection inside a fixed-height parent (h-96) with header sibling.",
        badges=[
            ("h-96 container", badge_colors.primary),
            ("flex constraint", badge_colors.secondary),
            ("auto-fit", badge_colors.accent),
        ],
    )
