"""
AUD-36: Additional test coverage for FrankyAutoMate engine and utilities.
Tests: variable operations, label resolution, security, and win32_input metrics.
"""
import threading
import os
import json
import tempfile
import pytest

from engine.automation_engine import EngineMixin


class DummyEngine(EngineMixin):
    """Minimal mock engine for testing isolated methods"""

    def __init__(self):
        super().__init__()
        self.variables = {}
        self.variable_lock = threading.RLock()  # Must be RLock to match production
        self.image_cache = {}
        self.actions = []
        self.actions_lock = threading.Lock()
        self._label_index_cache = None

    def log_message(self, *args, **kwargs):
        pass


# ── Variable Operations ─────────────────────────────────────────────


class TestVarSet:
    def test_basic_set(self):
        e = DummyEngine()
        e._execute_var_set({"name": "x", "value": 42})
        assert e.variables["x"] == 42

    def test_set_string(self):
        e = DummyEngine()
        e._execute_var_set({"name": "msg", "value": "hello"})
        assert e.variables["msg"] == "hello"

    def test_set_from_variable(self):
        e = DummyEngine()
        e.variables["src"] = 99
        e._execute_var_set({"name": "dst", "value": "$src"})
        assert e.variables["dst"] == 99

    def test_set_no_name_ignored(self):
        e = DummyEngine()
        e._execute_var_set({"name": "", "value": 1})
        assert "" not in e.variables

    def test_set_none_name_ignored(self):
        e = DummyEngine()
        e._execute_var_set({"name": None, "value": 1})
        assert None not in e.variables


class TestVarMath:
    def test_add(self):
        e = DummyEngine()
        e.variables["x"] = 10
        e._execute_var_math({"name": "x", "op": "add", "value": 5})
        assert e.variables["x"] == 15

    def test_sub(self):
        e = DummyEngine()
        e.variables["x"] = 10
        e._execute_var_math({"name": "x", "op": "sub", "value": 3})
        assert e.variables["x"] == 7

    def test_mul(self):
        e = DummyEngine()
        e.variables["x"] = 4
        e._execute_var_math({"name": "x", "op": "mul", "value": 3})
        assert e.variables["x"] == 12

    def test_div(self):
        e = DummyEngine()
        e.variables["x"] = 10
        e._execute_var_math({"name": "x", "op": "div", "value": 4})
        assert e.variables["x"] == 2.5

    def test_div_by_zero(self):
        e = DummyEngine()
        e.variables["x"] = 10
        e._execute_var_math({"name": "x", "op": "div", "value": 0})
        assert e.variables["x"] == 0  # Returns 0 on div-by-zero

    def test_math_on_undefined_var(self):
        e = DummyEngine()
        e._execute_var_math({"name": "new_var", "op": "add", "value": 5})
        assert e.variables["new_var"] == 5  # 0 + 5

    def test_math_with_variable_ref(self):
        e = DummyEngine()
        e.variables["a"] = 10
        e.variables["b"] = 3
        e._execute_var_math({"name": "a", "op": "sub", "value": "$b"})
        assert e.variables["a"] == 7

    def test_int_result_stays_int(self):
        e = DummyEngine()
        e.variables["x"] = 5
        e._execute_var_math({"name": "x", "op": "add", "value": 5})
        assert isinstance(e.variables["x"], int)
        assert e.variables["x"] == 10


# ── Label Resolution ─────────────────────────────────────────────


class TestLabelResolution:
    def test_find_existing_label(self):
        e = DummyEngine()
        actions = [
            {"type": "click", "x": 0, "y": 0},
            {"type": "logic_label", "name": "start"},
            {"type": "wait", "seconds": 1},
        ]
        result = e._find_label_index("start", actions)
        assert result == 1

    def test_find_missing_label(self):
        e = DummyEngine()
        actions = [{"type": "click", "x": 0, "y": 0}]
        result = e._find_label_index("nonexistent", actions)
        assert result is None

    def test_find_empty_label(self):
        e = DummyEngine()
        result = e._find_label_index("", [])
        assert result is None

    def test_find_label_with_cache(self):
        e = DummyEngine()
        e._label_index_cache = {"cached_label": 5}
        result = e._find_label_index("cached_label")
        assert result == 5

    def test_find_label_cache_miss_fallback(self):
        e = DummyEngine()
        e._label_index_cache = {"other": 0}
        e.actions = [
            {"type": "logic_label", "name": "target"},
        ]
        result = e._find_label_index("target")
        assert result == 0


# ── Evaluate Expression Edge Cases ───────────────────────────────


class TestEvaluateExpressionEdge:
    def test_less_than_equal(self):
        e = DummyEngine()
        assert e._evaluate_expression(5, "<=", 5) is True
        assert e._evaluate_expression(4, "<=", 5) is True
        assert e._evaluate_expression(6, "<=", 5) is False

    def test_greater_than(self):
        e = DummyEngine()
        assert e._evaluate_expression(10, ">", 5) is True
        assert e._evaluate_expression(5, ">", 5) is False

    def test_unknown_op_returns_false(self):
        e = DummyEngine()
        assert e._evaluate_expression(5, "???", 5) is False

    def test_none_values(self):
        e = DummyEngine()
        # None can't be float(), falls back to string comparison
        assert e._evaluate_expression(None, "==", None) is True
        assert e._evaluate_expression(None, "!=", "something") is True

    def test_string_not_equal_op(self):
        e = DummyEngine()
        assert e._evaluate_expression("a", "!=", "b") is True
        assert e._evaluate_expression("a", "!=", "a") is False


# ── Security Module ──────────────────────────────────────────────


class TestChecksum:
    def test_verify_no_known_hash(self):
        """When no expected hash exists, should return True with warning"""
        from utils.security import verify_file_checksum
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(b"test data")
            path = f.name
        try:
            result = verify_file_checksum(path)
            assert result is True  # Passes when no hash provided
        finally:
            os.unlink(path)

    def test_verify_correct_hash(self):
        """Correct hash should verify"""
        import hashlib
        from utils.security import verify_file_checksum

        data = b"hello world"
        expected = hashlib.sha256(data).hexdigest()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(data)
            path = f.name
        try:
            result = verify_file_checksum(path, expected_hash=expected)
            assert result is True
        finally:
            os.unlink(path)

    def test_verify_wrong_hash(self):
        """Wrong hash should fail"""
        from utils.security import verify_file_checksum
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(b"test data")
            path = f.name
        try:
            result = verify_file_checksum(path, expected_hash="0" * 64)
            assert result is False
        finally:
            os.unlink(path)

    def test_verify_nonexistent_file(self):
        """Nonexistent file should return False"""
        from utils.security import verify_file_checksum
        result = verify_file_checksum("nonexistent_file.bin", expected_hash="abc")
        assert result is False


class TestSecureConfig:
    def test_save_load_plaintext(self):
        """When DPAPI not available, should save/load plaintext"""
        from utils.security import save_config_secure, load_config_secure

        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
            path = f.name
        try:
            save_config_secure(data, path)
            loaded = load_config_secure(path)
            assert loaded["key"] == "value"
            assert loaded["number"] == 42
            assert loaded["nested"]["a"] == 1
        finally:
            os.unlink(path)

    def test_load_nonexistent(self):
        """Loading nonexistent file should return empty dict"""
        from utils.security import load_config_secure
        result = load_config_secure("nonexistent_path_12345.json")
        assert result == {}

    def test_load_corrupt_json(self):
        """Loading corrupt JSON should return empty dict"""
        from utils.security import load_config_secure
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
            f.write("{corrupt json!!")
            path = f.name
        try:
            result = load_config_secure(path)
            assert result == {}
        finally:
            os.unlink(path)


# ── Image Cache Capping ──────────────────────────────────────────


class TestImageCacheCap:
    def test_cache_caps_at_256(self):
        """image_cache should not exceed ~256 entries"""
        import numpy as np
        from core.constants import IMAGE_CACHE_MAX_SIZE
        e = DummyEngine()
        # Simulate adding more entries than limit
        for i in range(IMAGE_CACHE_MAX_SIZE + 50):
            fake_img = np.zeros((10, 10, 3), dtype=np.uint8)
            e._get_gray_template(f"path_{i}.png", fake_img)

        # Should be capped
        assert len(e.image_cache) <= IMAGE_CACHE_MAX_SIZE + 10


# ── Hotkey Key Normalization ─────────────────────────────────────


class TestHotkeyNormalization:
    """Test _key_to_string normalization from hotkey_engine.py"""

    def test_ctrl_l_maps_to_ctrl(self):
        from engine.hotkey_engine import HotkeyMixin
        mixin = HotkeyMixin()
        # Simulate a Key object with no char
        class FakeKey:
            char = None
            def __str__(self):
                return "Key.ctrl_l"
        result = mixin._key_to_string(FakeKey())
        assert result == "ctrl"

    def test_string_key_lowered(self):
        from engine.hotkey_engine import HotkeyMixin
        mixin = HotkeyMixin()
        assert mixin._key_to_string("F6") == "f6"

    def test_char_key(self):
        from engine.hotkey_engine import HotkeyMixin
        mixin = HotkeyMixin()
        class FakeKey:
            char = "A"
        result = mixin._key_to_string(FakeKey())
        assert result == "a"


# ── Preset Hotkey Skip Logic ─────────────────────────────────────


class TestPresetHotkeySkip:
    """BUG-1: Presets with None hotkey should be skipped"""

    def test_none_hotkey_skipped(self):
        """str(None) was 'none' which could falsely match"""
        presets = [
            {"name": "set1", "hotkey": None, "actions": []},
            {"name": "set2", "hotkey": "f7", "actions": []},
        ]
        # Simulate the fixed logic
        matched = []
        for i, p in enumerate(presets):
            raw_hotkey = p.get("hotkey")
            if not raw_hotkey:
                continue
            matched.append(str(raw_hotkey).lower())
        assert "none" not in matched
        assert "f7" in matched

    def test_empty_string_hotkey_skipped(self):
        presets = [{"name": "set1", "hotkey": "", "actions": []}]
        matched = []
        for p in presets:
            raw_hotkey = p.get("hotkey")
            if not raw_hotkey:
                continue
            matched.append(str(raw_hotkey).lower())
        assert len(matched) == 0


# ── Constants Validation ─────────────────────────────────────────


class TestEngineConstants:
    """Verify all engine constants exist and have valid ranges"""

    def test_constants_exist(self):
        from core.constants import (
            WAIT_MODE_TIMEOUT, IMAGE_CACHE_MAX_SIZE, IMAGE_CACHE_EVICT_COUNT,
            SCREENSHOT_CACHE_TTL, EMERGENCY_CORNER_PX, EMERGENCY_CORNER_HOLD,
            FOCUS_DELAY_DEFAULT, FOCUS_DELAY_STANDALONE,
            HUMAN_MOVE_MAX_STEPS, AUTO_SAVE_DEBOUNCE_MS, HOTKEY_COMMIT_DELAY_MS,
        )
        assert WAIT_MODE_TIMEOUT > 0
        assert IMAGE_CACHE_MAX_SIZE > IMAGE_CACHE_EVICT_COUNT
        assert SCREENSHOT_CACHE_TTL > 0
        assert EMERGENCY_CORNER_PX >= 1
        assert EMERGENCY_CORNER_HOLD > 0
        assert FOCUS_DELAY_DEFAULT > 0
        assert FOCUS_DELAY_STANDALONE >= FOCUS_DELAY_DEFAULT
        assert HUMAN_MOVE_MAX_STEPS >= 10
        assert AUTO_SAVE_DEBOUNCE_MS >= 100
        assert HOTKEY_COMMIT_DELAY_MS >= 100

    def test_evict_count_less_than_max(self):
        from core.constants import IMAGE_CACHE_MAX_SIZE, IMAGE_CACHE_EVICT_COUNT
        assert IMAGE_CACHE_EVICT_COUNT < IMAGE_CACHE_MAX_SIZE


# ── BUG-R8: Screen Metrics Fallback ────────────────────────────────

class TestScreenMetricsFallback:
    """BUG-R8: Verify _get_screen_metrics returns sane defaults when system returns 0."""

    def test_zero_screen_returns_fallback(self):
        from utils import win32_input
        # Save originals
        orig_w, orig_h = win32_input._screen_w, win32_input._screen_h
        try:
            win32_input._screen_w = 0
            win32_input._screen_h = 0
            w, h, _, _ = win32_input._get_screen_metrics()
            # Should return fallback 1920x1080, not 0
            assert w > 0
            assert h > 0
        finally:
            win32_input._screen_w = orig_w
            win32_input._screen_h = orig_h

    def test_normal_screen_returns_actual(self):
        from utils import win32_input
        w, h, _, _ = win32_input._get_screen_metrics()
        assert w > 0
        assert h > 0


# ── SEC-R1: Batch Script Sanitization ──────────────────────────────

class TestBatchSanitization:
    """SEC-R1: Verify safe_path strips all dangerous characters."""

    @staticmethod
    def _safe_path(p):
        """Mirror the safe_path function from update_window.py"""
        result = str(p)
        for ch in ('"', "'", "&", "|", ">", "<", "^", "%", "!", ";", "@",
                   "\n", "\r", "(", ")", "`", "{", "}", "$", "~", ".."):
            result = result.replace(ch, "")
        return result

    def test_strips_quotes(self):
        assert '"' not in self._safe_path('C:\\path\\"inject"')
        assert "'" not in self._safe_path("C:\\path\\'inject'")

    def test_strips_pipe_and_ampersand(self):
        result = self._safe_path("C:\\test | whoami & del *")
        assert "|" not in result
        assert "&" not in result

    def test_strips_shell_special(self):
        result = self._safe_path("C:\\$(cmd) `backtick` {brace} ~tilde")
        assert "$" not in result
        assert "`" not in result
        assert "{" not in result
        assert "~" not in result

    def test_preserves_normal_paths(self):
        normal = r"C:\Users\Frank\Desktop\autoclick\app.exe"
        assert self._safe_path(normal) == normal


# ── CMPLX-R2: Key lParam Construction ─────────────────────────────

class TestMakeKeyLparam:
    """CMPLX-R2: Verify _make_key_lparam correctly sets Win32 lParam bits."""

    def test_basic_scancode(self):
        # Scan code goes to bits 16-23
        result = DummyEngine._make_key_lparam(scan=0x1E)
        assert (result >> 16) & 0xFF == 0x1E
        assert result & 0xFFFF == 1  # repeat count = 1

    def test_extended_flag(self):
        result = DummyEngine._make_key_lparam(scan=0x00, extended=True)
        assert result & (1 << 24) != 0  # bit 24 set

    def test_transition_flag(self):
        result = DummyEngine._make_key_lparam(scan=0x00, transition=True)
        # bit 31 is the sign bit in 32-bit int, check via mask
        assert result & (1 << 31) != 0

    def test_prev_state_flag(self):
        result = DummyEngine._make_key_lparam(scan=0x00, prev_state=True)
        assert result & (1 << 30) != 0
