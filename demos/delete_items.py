"""Delete Items demo — tests build_items_changed_response for external item removal.

Showcases targeted OOB container replacement after deleting items from the
virtual collection, including edge cases: cursor clamping, window shrinking,
and transitioning to fewer items than visible_rows.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import random


@dataclass
class DemoItem:
    """Sample item for delete demo."""
    id: int
    name: str
    category: str


def setup():
    """Set up the delete items demo page."""
    from fasthtml.common import (
        Div, H2, P, Button, Span, Script, APIRouter,
    )

    from cjm_fasthtml_daisyui.components.actions.button import btn, btn_colors, btn_sizes
    from cjm_fasthtml_daisyui.components.data_display.badge import badge, badge_styles
    from cjm_fasthtml_daisyui.utilities.semantic_colors import text_dui

    from cjm_fasthtml_tailwind.utilities.spacing import p, m
    from cjm_fasthtml_tailwind.utilities.sizing import container, max_w
    from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight
    from cjm_fasthtml_tailwind.core.base import combine_classes

    from cjm_fasthtml_keyboard_navigation.core.manager import ZoneManager
    from cjm_fasthtml_keyboard_navigation.components.system import render_keyboard_system

    from cjm_fasthtml_virtual_collection.core.models import (
        VirtualCollectionConfig, VirtualCollectionState, ColumnDef,
    )
    from cjm_fasthtml_virtual_collection.core.html_ids import VirtualCollectionHtmlIds
    from cjm_fasthtml_virtual_collection.core.button_ids import VirtualCollectionButtonIds
    from cjm_fasthtml_virtual_collection.components.collection import render_virtual_collection
    from cjm_fasthtml_virtual_collection.routes.router import init_virtual_collection_router
    from cjm_fasthtml_virtual_collection.routes.handlers import build_items_changed_response
    from cjm_fasthtml_virtual_collection.keyboard.actions import (
        create_collection_focus_zone, create_collection_nav_actions,
        build_collection_url_map, apply_nav_sync,
    )
    from cjm_fasthtml_virtual_collection.js.scroll import generate_scroll_nav_js
    from cjm_fasthtml_virtual_collection.js.scrollbar import generate_scrollbar_js
    from cjm_fasthtml_virtual_collection.js.auto_fit import generate_auto_fit_js, auto_fit_callback_name

    from cjm_fasthtml_viewport_fit.models import ViewportFitConfig
    from cjm_fasthtml_viewport_fit.components import render_viewport_fit_script

    # -------------------------------------------------------------------------
    # Data
    # -------------------------------------------------------------------------

    ITEM_COUNT = 20

    categories = ["alpha", "beta", "gamma", "delta"]
    items = [
        DemoItem(id=i, name=f"Item {i:03d}", category=categories[i % len(categories)])
        for i in range(ITEM_COUNT)
    ]
    _next_id = [ITEM_COUNT]  # Mutable counter for new item IDs

    # -------------------------------------------------------------------------
    # VC config & state
    # -------------------------------------------------------------------------

    config = VirtualCollectionConfig(
        prefix="del_demo",
        columns=(
            ColumnDef(key="id", header="#", sortable=True),
            ColumnDef(key="name", header="Name", sortable=True),
            ColumnDef(key="category", header="Category"),
        ),
    )

    state = VirtualCollectionState(
        total_items=len(items),
        visible_rows=1,
        cursor_index=0,
    )

    ids = VirtualCollectionHtmlIds(prefix=config.prefix)
    btn_ids = VirtualCollectionButtonIds(prefix=config.prefix)

    STATS_ID = "del-demo-stats"

    # -------------------------------------------------------------------------
    # Cell renderer
    # -------------------------------------------------------------------------

    def render_cell(item, ctx):
        if ctx.column.key == "id":
            return Span(str(item.id))
        elif ctx.column.key == "name":
            return Span(item.name, cls=str(font_weight.medium))
        elif ctx.column.key == "category":
            return Span(item.category, cls=combine_classes(badge, badge_styles.ghost))
        return Span("")

    # -------------------------------------------------------------------------
    # Stats bar helper
    # -------------------------------------------------------------------------

    def _render_stats():
        return P(
            f"{len(items)} items · cursor={state.cursor_index} · "
            f"window={state.window_start} · visible={state.visible_rows}",
            id=STATS_ID,
            cls=combine_classes(text_dui.base_content, font_size.sm, m.b(2)),
        )

    # -------------------------------------------------------------------------
    # VC router
    # -------------------------------------------------------------------------

    def sort_items(items_list, column_key, ascending):
        key_map = {"id": lambda x: x.id, "name": lambda x: x.name}
        key_fn = key_map.get(column_key)
        if key_fn:
            items_list.sort(key=key_fn, reverse=not ascending)

    vc_router, urls = init_virtual_collection_router(
        config=config,
        state_getter=lambda: state,
        state_setter=lambda s: None,
        get_items=lambda: items,
        render_cell=render_cell,
        sort_callback=sort_items,
        route_prefix="/del_demo/vc",
    )

    # -------------------------------------------------------------------------
    # Mutation routes
    # -------------------------------------------------------------------------

    _refit = auto_fit_callback_name(config)
    demo_router = APIRouter(prefix="/del_demo")

    @demo_router.post
    def delete_focused():
        """Delete the currently focused item via targeted OOB."""
        if not items or state.cursor_index < 0:
            return ()

        idx = state.cursor_index
        items.pop(idx)

        # Use the new public API
        vc_oobs = build_items_changed_response(
            items, state, config, ids, render_cell,
            focus_url=urls.focus_row, refit_callback=_refit,
        )

        # Also update stats bar via OOB
        stats = _render_stats()
        stats.attrs['hx-swap-oob'] = 'outerHTML'

        return (*vc_oobs, stats)

    @demo_router.post
    def delete_all():
        """Delete all items."""
        items.clear()
        vc_oobs = build_items_changed_response(
            items, state, config, ids, render_cell,
            refit_callback=_refit,
        )
        stats = _render_stats()
        stats.attrs['hx-swap-oob'] = 'outerHTML'
        return (*vc_oobs, stats)

    @demo_router.post
    def add_item():
        """Add a new item after the cursor position."""
        new_id = _next_id[0]
        _next_id[0] += 1
        new_item = DemoItem(
            id=new_id,
            name=f"Item {new_id:03d}",
            category=categories[new_id % len(categories)],
        )
        # Insert after cursor (or at end if no cursor)
        insert_idx = (state.cursor_index + 1) if state.cursor_index >= 0 else len(items)
        items.insert(insert_idx, new_item)

        vc_oobs = build_items_changed_response(
            items, state, config, ids, render_cell,
            focus_url=urls.focus_row, refit_callback=_refit,
        )
        stats = _render_stats()
        stats.attrs['hx-swap-oob'] = 'outerHTML'
        return (*vc_oobs, stats)

    @demo_router.post
    def reset_items():
        """Reset to original ITEM_COUNT items."""
        items.clear()
        items.extend([
            DemoItem(id=i, name=f"Item {i:03d}", category=categories[i % len(categories)])
            for i in range(ITEM_COUNT)
        ])
        _next_id[0] = ITEM_COUNT
        vc_oobs = build_items_changed_response(
            items, state, config, ids, render_cell,
            focus_url=urls.focus_row, refit_callback=_refit,
        )
        stats = _render_stats()
        stats.attrs['hx-swap-oob'] = 'outerHTML'
        return (*vc_oobs, stats)

    # -------------------------------------------------------------------------
    # Keyboard system
    # -------------------------------------------------------------------------

    zone = create_collection_focus_zone(ids)
    nav_actions = create_collection_nav_actions(zone.id, btn_ids)
    manager = ZoneManager(zones=(zone,), actions=nav_actions)

    url_map = build_collection_url_map(btn_ids, urls)
    target_map = {bid: f"#{ids.rows}" for bid in url_map}
    swap_map = {bid: "none" for bid in url_map}

    kb_system = render_keyboard_system(
        manager, url_map=url_map, target_map=target_map, swap_map=swap_map,
    )
    apply_nav_sync(kb_system, ids)

    # -------------------------------------------------------------------------
    # Page content
    # -------------------------------------------------------------------------

    vf_config = ViewportFitConfig(
        namespace=config.prefix,
        target_id=ids.wrapper,
        resize_callback=auto_fit_callback_name(config),
        enable_htmx_settle=False,
    )

    def page_content():
        auto_fit_js = generate_auto_fit_js(
            ids, config, urls,
            total_items=len(items),
            initial_visible=state.visible_rows,
        )

        return Div(
            H2("Delete Items Demo",
               cls=combine_classes(font_size._2xl, font_weight.bold, m.b(2))),
            P("Tests build_items_changed_response — targeted OOB container "
              "replacement after external item mutations.",
              cls=combine_classes(text_dui.base_content, m.b(4))),

            # Action buttons
            Div(
                Button("Delete Focused", cls=combine_classes(btn, btn_colors.error, btn_sizes.sm),
                       hx_post=delete_focused.to(), hx_swap="none"),
                Button("Add Item", cls=combine_classes(btn, btn_colors.success, btn_sizes.sm),
                       hx_post=add_item.to(), hx_swap="none"),
                Button("Delete All", cls=combine_classes(btn, btn_colors.warning, btn_sizes.sm),
                       hx_post=delete_all.to(), hx_swap="none"),
                Button(f"Reset ({ITEM_COUNT} items)", cls=combine_classes(btn, btn_sizes.sm),
                       hx_post=reset_items.to(), hx_swap="none"),
                cls=combine_classes("flex gap-2", m.b(4)),
            ),

            # Stats
            _render_stats(),

            # Virtual collection
            render_virtual_collection(
                items=items, config=config, state=state,
                ids=ids, urls=urls, render_cell=render_cell,
            ),

            # Keyboard system
            kb_system.script,
            kb_system.hidden_inputs,
            kb_system.action_buttons,

            # JS
            Script(generate_scroll_nav_js(ids, btn_ids)),
            Script(generate_scrollbar_js(ids, urls)),
            Script(auto_fit_js),
            render_viewport_fit_script(vf_config),

            cls=combine_classes(container, max_w._4xl, m.x.auto, p(4)),
        )

    return {
        "title": "Delete Items",
        "router": demo_router,
        "vc_router": vc_router,
        "page_content": page_content,
    }
