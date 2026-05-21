"""
Protocol classes for Mixin type safety.

Defines the interface that each Mixin expects from the host class (AutoMationApp).
Type checkers (mypy, pyright) can validate attribute access across mixins.

Usage:
    Each mixin can use `if TYPE_CHECKING: from core.protocols import AppProtocol`
    and annotate `self: AppProtocol` in methods where cross-mixin access is needed.
"""

from __future__ import annotations

import threading
from typing import (
    Any,
    Protocol,
    runtime_checkable,
)


@runtime_checkable
class AppProtocol(Protocol):
    """
    Protocol defining the complete interface that AutoMationApp provides
    to all of its mixins.
    """

    # Core State
    is_running: bool
    is_paused: bool
    actions: list[dict[str, Any]]
    actions_lock: threading.Lock
    variables: dict[str, Any]
    variable_lock: threading.RLock
    presets: list[dict[str, Any]]
    current_preset_index: int
    target_hwnd: int | None
    target_title: str
    original_title: str
    speed_delay: float

    # UI Widgets
    lbl_status: Any
    lbl_target: Any
    btn_run: Any
    entry_loop: Any
    preset_dropdown: Any
    entry_preset_name: Any
    lbl_preset_hotkey: Any

    # Threading
    next_step: threading.Event
    execution_thread: threading.Thread | None

    # Configuration Vars
    var_step_mode: Any
    var_dry_run: Any
    var_follow_window: Any
    var_stealth_hide_window: Any
    var_stealth_random_title: Any
    var_stealth_move: Any
    var_stealth_sendinput: Any
    toggle_key: str

    # Caches
    image_cache: dict[Any, Any]
    screenshot_cache: Any | None
    _screenshot_lock: threading.Lock
    perf_metrics: dict[str, Any]

    # Picker State
    picked_x_raw: int
    picked_y_raw: int
    picked_rel_x: int
    picked_rel_y: int
    is_relative: bool
    show_marker: bool
    current_region: Any | None
    temp_multi_points: list[dict[str, Any]]
    _pending_after_ids: list[Any]

    # Host methods
    def after(self, ms: int, func: Any = ..., *args: Any) -> str: ...
    def after_cancel(self, id: str) -> None: ...
    def title(self, string: str = ...) -> str | None: ...
    def withdraw(self) -> None: ...
    def deiconify(self) -> None: ...
    def iconify(self) -> None: ...
    def lift(self) -> None: ...
    def focus_get(self) -> Any | None: ...
    def winfo_exists(self) -> bool: ...

    # Cross-mixin methods
    def log_message(self, message: str, color: str = ..., level: int = ...) -> None: ...
    def safe_update_ui(self, widget_name: str, **kwargs: Any) -> None: ...
    def update_list_display(self) -> None: ...
    def auto_save_presets(self) -> None: ...
    def add_action_item(self, action_data: dict[str, Any]) -> None: ...
    def refresh_label_dropdowns(self) -> None: ...
    def highlight_action(self, index: int) -> None: ...
    def setup_hotkeys(self) -> None: ...
    def stealth_on_run_start(self) -> None: ...
    def stealth_on_run_stop(self) -> None: ...
    def get_cached_screenshot(self, region: Any = ..., as_gray: bool = ...) -> Any: ...
    def calculate_picked_coords(self) -> None: ...
    def get_current_preset(self) -> dict[str, Any] | None: ...
    def update_preset_ui(self) -> None: ...
    def _track_after(self, ms: int, func: Any) -> str: ...
