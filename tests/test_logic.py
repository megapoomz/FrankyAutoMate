from engine.automation_engine import EngineMixin


class DummyEngine(EngineMixin):
    """A minimal mock engine to test isolated logic methods safely"""

    def __init__(self):
        super().__init__()
        self.variables = {}

    def log_message(self, *args, **kwargs):
        pass  # Override UI logging


def test_resolve_value_numeric():
    engine = DummyEngine()
    engine.variables["count"] = 10

    # Resolving literal
    assert engine._resolve_value("5") == "5"

    # Resolving variable
    assert engine._resolve_value("$count") == 10

    # Resolving undefined variable
    assert engine._resolve_value("$missing") == 0


def test_evaluate_expression_numeric():
    engine = DummyEngine()

    # Direct numeric comparison
    assert engine._evaluate_expression(10, "==", 10) is True
    assert engine._evaluate_expression(10, "!=", 5) is True
    assert engine._evaluate_expression(5, "<", 10) is True
    assert engine._evaluate_expression(10, ">=", 10) is True

    # Mixed string-numeric comparison (floats)
    assert engine._evaluate_expression("15.5", "==", 15.5) is True
    assert engine._evaluate_expression("20", ">", "10") is True


def test_evaluate_expression_string():
    engine = DummyEngine()

    assert engine._evaluate_expression("hello", "==", "hello") is True
    assert engine._evaluate_expression("hello", "!=", "world") is True

    # Fallback > on strings returns False generally in this implementation
    assert engine._evaluate_expression("abc", ">", "xyz") is False


def test_evaluate_expression_with_variables():
    engine = DummyEngine()
    engine.variables["health"] = 100
    engine.variables["status"] = "poisoned"

    assert engine._evaluate_expression("$health", ">", 50) is True
    assert engine._evaluate_expression("$health", "==", 100) is True
    assert engine._evaluate_expression("$status", "==", "poisoned") is True
    assert engine._evaluate_expression("$status", "!=", "healthy") is True
