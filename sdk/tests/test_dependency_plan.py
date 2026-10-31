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

    def test_dependency_declaration_cannot_be_a_string(self):
        with self.assertRaisesRegex(planner.DependencyPlanError, "not text"):
            planner.resolve_install_order(["app"], {"app": "library"})

    def test_non_string_or_unhashable_dependency_fails_closed(self):
        for dependency in (None, {}, 7, ""):
            with self.subTest(dependency=dependency):
                with self.assertRaises(planner.DependencyPlanError):
                    planner.resolve_install_order(["app"], {"app": [dependency]})

    def test_roots_must_be_package_id_strings(self):
        for roots in ("app", ["app", None], [[]]):
            with self.subTest(roots=roots):
                with self.assertRaises(planner.DependencyPlanError):
                    planner.resolve_install_order(roots, {"app": []})

    def test_deep_dependency_chain_does_not_hit_python_recursion_limit(self):
        depth = 1500
        graph = {
            f"pkg-{index}": ([f"pkg-{index + 1}"] if index + 1 < depth else [])
            for index in range(depth)
        }
        order = planner.resolve_install_order(["pkg-0"], graph)
        self.assertEqual(len(order), depth)
        self.assertEqual(order[0], f"pkg-{depth - 1}")
        self.assertEqual(order[-1], "pkg-0")

    def test_iterative_cycle_error_includes_cycle_path(self):
        graph = {"a": ["b"], "b": ["c"], "c": ["a"]}
        with self.assertRaisesRegex(
            planner.DependencyPlanError, r"dependency cycle: a -> b -> c -> a"
        ):
            planner.resolve_install_order(["a"], graph)

    def test_packages_must_be_a_mapping(self):
        with self.assertRaisesRegex(planner.DependencyPlanError, "mapping"):
            planner.resolve_install_order(["app"], [("app", [])])


if __name__ == "__main__":
    unittest.main()
