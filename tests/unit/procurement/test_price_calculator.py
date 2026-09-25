import asyncio
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

# Open WebUI injects fastapi at runtime; the calculator itself does not use it.
fastapi_stub = types.ModuleType("fastapi")
fastapi_stub.Request = object
sys.modules.setdefault("fastapi", fastapi_stub)


ROOT = Path(__file__).resolve().parents[3]
PIPE_PATH = ROOT / "app/openwebui/functions/procurement_price_pipe.py"
TOOL_PATH = ROOT / "app/openwebui/tools/procurement-search.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pipe_module = load_module("procurement_price_pipe", PIPE_PATH)
tool_module = load_module("procurement_search", TOOL_PATH)

TIERS = [
    {"quantity_label": "1-50", "quantity_min": 1, "quantity_max": 50, "awarded_price": 16.2},
    {"quantity_label": "51-100", "quantity_min": 51, "quantity_max": 100, "awarded_price": 11.5},
    {"quantity_label": "101-200", "quantity_min": 101, "quantity_max": 200, "awarded_price": 9.2},
]


class PriceCalculatorTests(unittest.TestCase):
    def pipe_calculate(self, quantity, tiers=TIERS):
        raw = pipe_module.Pipe()._calculate_total_price({"quantity": quantity, "tiers": tiers})
        return json.loads(raw)

    def test_pipe_calculator_selects_exact_tier_boundaries(self):
        cases = [(1, 16.2, 16.2), (50, 16.2, 810.0), (51, 11.5, 586.5),
                 (100, 11.5, 1150.0), (101, 9.2, 929.2)]
        for quantity, unit_price, total in cases:
            with self.subTest(quantity=quantity):
                result = self.pipe_calculate(quantity)
                self.assertTrue(result["success"])
                self.assertEqual(result["unit_price"], unit_price)
                self.assertEqual(result["total_price"], total)

    def test_pipe_calculator_reports_below_moq(self):
        result = self.pipe_calculate(5, [
            {"quantity_label": "10-20", "quantity_min": 10, "quantity_max": 20, "awarded_price": 7.5}
        ])
        self.assertTrue(result["success"])
        self.assertTrue(result["below_moq"])
        self.assertEqual(result["moq"], 10)
        self.assertEqual(result["total_at_moq"], 75.0)
        self.assertNotIn("total_price", result)

    def test_pipe_calculator_rejects_quantity_gap(self):
        result = self.pipe_calculate(15, [
            {"quantity_label": "1-10", "quantity_min": 1, "quantity_max": 10, "awarded_price": 5},
            {"quantity_label": "20-30", "quantity_min": 20, "quantity_max": 30, "awarded_price": 4},
        ])
        self.assertFalse(result["success"])
        self.assertEqual(result["reason"], "no_matching_tier")

    def test_pipe_exposes_and_dispatches_calculator_tool(self):
        names = {item["function"]["name"] for item in pipe_module.TOOLS}
        self.assertIn("calculate_total_price", names)
        raw = pipe_module.Pipe()._dispatch_tool(
            "calculate_total_price", {"quantity": 100, "tiers": TIERS}
        )
        self.assertEqual(json.loads(raw)["total_price"], 1150.0)

    def test_openwebui_tool_calculator_matches_pipe_result(self):
        raw = asyncio.run(tool_module.Tools().calculate_total_price(quantity=100, tiers=TIERS))
        result = json.loads(raw)
        self.assertEqual(result["unit_price"], 11.5)
        self.assertEqual(result["total_price"], 1150.0)

    def test_openwebui_tool_calculator_rejects_quantity_gap(self):
        raw = asyncio.run(tool_module.Tools().calculate_total_price(quantity=15, tiers=[
            {"quantity_label": "1-10", "quantity_min": 1, "quantity_max": 10, "awarded_price": 5},
            {"quantity_label": "20-30", "quantity_min": 20, "quantity_max": 30, "awarded_price": 4},
        ]))
        result = json.loads(raw)
        self.assertFalse(result["success"])
        self.assertEqual(result["reason"], "no_matching_tier")


if __name__ == "__main__":
    unittest.main()
