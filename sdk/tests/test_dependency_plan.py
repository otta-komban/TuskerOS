"""Tests for deterministic dependency ordering (no installer side effects)."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dependency_plan", ROOT / "tools" / "dependency_plan.py")
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)


class DependencyPlanTests(unittest.TestCase):
    def test_dependencies_precede_dependents(self):
        graph = {"app": ["lib"], "lib": ["base"], "base": []}
        self.assertEqual(planner.resolve_install_order(["app"], graph), ["base", "lib", "app"])

    def test_shared_dependencies_are_emitted_once(self):
        graph = {"app-a": ["shared"], "app-b": ["shared"], "shared": []}
        result = planner.resolve_install_order(["app-b", "app-a"], graph)
        self.assertEqual(result.count("shared"), 1)
        self.assertLess(result.index("shared"), result.index("app-a"))
        self.assertLess(result.index("shared"), result.index("app-b"))

    def test_independent_nodes_are_deterministic(self):
        graph = {"z": [], "a": []}
        self.assertEqual(planner.resolve_install_order(["z", "a"], graph), ["a", "z"])

    def test_missing_root_fails_closed(self):
        with self.assertRaises(planner.DependencyPlanError):
            planner.resolve_install_order(["absent"], {})

    def test_missing_dependency_fails_closed(self):
        with self.assertRaises(planner.DependencyPlanError):
            planner.resolve_install_order(["app"], {"app": ["absent"]})

    def test_cycle_fails_closed(self):
        with self.assertRaisesRegex(planner.DependencyPlanError, "dependency cycle"):
            planner.resolve_install_order(["a"], {"a": ["b"], "b": ["a"]})

    def test_duplicate_dependency_fails_closed(self):
        with self.assertRaisesRegex(planner.DependencyPlanError, "duplicate dependency"):
            planner.resolve_install_order(["app"], {"app": ["lib", "lib"], "lib": []})


if __name__ == "__main__":
    unittest.main()
