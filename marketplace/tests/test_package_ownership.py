import copy
import unittest

from marketplace.tools.package_ownership import (
    OwnershipPlanError,
    plan_owner_removal,
    validate_installed_state,
)


class PackageOwnershipTests(unittest.TestCase):
    def state(self):
        return {
            "state_version": 1,
            "packages": [
                {"package_id": "app.demo", "version": "1.0.0",
                 "owners": [{"kind": "bundle", "id": "python"}],
                 "dependencies": ["lib.shared", "lib.private"]},
                {"package_id": "lib.shared", "version": "2.0.0",
                 "owners": [{"kind": "bundle", "id": "python"},
                            {"kind": "bundle", "id": "data"}],
                 "dependencies": []},
                {"package_id": "lib.private", "version": "1.2.0",
                 "owners": [{"kind": "bundle", "id": "python"}],
                 "dependencies": ["lib.leaf"]},
                {"package_id": "lib.leaf", "version": "1.0.0",
                 "owners": [{"kind": "bundle", "id": "python"}],
                 "dependencies": []},
                {"package_id": "manual.tool", "version": "3.0.0",
                 "owners": [{"kind": "user", "id": "local-user"}],
                 "dependencies": ["lib.shared"]},
                {"package_id": "os.base", "version": "40.0.0",
                 "owners": [{"kind": "system", "id": "fedora"}],
                 "dependencies": []},
            ],
        }

    def test_removes_exclusive_packages_and_transitive_dependencies(self):
        plan = plan_owner_removal(self.state(), "bundle", "python")
        self.assertEqual(
            [item["package_id"] for item in plan["remove"]],
            ["app.demo", "lib.leaf", "lib.private"],
        )
        self.assertIn("lib.shared", [item["package_id"] for item in plan["keep"]])

    def test_shared_dependency_is_preserved(self):
        plan = plan_owner_removal(self.state(), "bundle", "python")
        shared = next(x for x in plan["keep"] if x["package_id"] == "lib.shared")
        self.assertIn("bundle:data", shared["reason"])

    def test_user_and_system_packages_are_never_candidates(self):
        plan = plan_owner_removal(self.state(), "bundle", "python")
        keep_ids = {item["package_id"] for item in plan["keep"]}
        self.assertTrue({"manual.tool", "os.base"} <= keep_ids)
        self.assertNotIn("manual.tool", [item["package_id"] for item in plan["remove"]])

    def test_package_referenced_by_non_target_owner_is_protected(self):
        state = self.state()
        state["packages"].append({
            "package_id": "other.app", "version": "1.0.0",
            "owners": [{"kind": "extension", "id": "other"}],
            "dependencies": ["lib.private"],
        })
        plan = plan_owner_removal(state, "bundle", "python")
        remove_ids = {item["package_id"] for item in plan["remove"]}
        self.assertFalse({"lib.private", "lib.leaf"} & remove_ids)

    def test_missing_owner_fails_closed(self):
        with self.assertRaisesRegex(OwnershipPlanError, "owner not found"):
            plan_owner_removal(self.state(), "bundle", "missing")

    def test_user_or_system_owner_cannot_be_removed(self):
        with self.assertRaisesRegex(OwnershipPlanError, "only bundle or extension"):
            plan_owner_removal(self.state(), "user", "local-user")

    def test_missing_dependency_reference_fails_closed(self):
        state = self.state()
        state["packages"][0]["dependencies"] = ["missing.package"]
        with self.assertRaisesRegex(OwnershipPlanError, "missing installed dependency"):
            validate_installed_state(state)

    def test_duplicate_package_and_owner_records_fail_closed(self):
        state = self.state()
        state["packages"].append(copy.deepcopy(state["packages"][0]))
        with self.assertRaisesRegex(OwnershipPlanError, "duplicate installed package"):
            validate_installed_state(state)

        state = self.state()
        state["packages"][0]["owners"].append({"kind": "bundle", "id": "python"})
        with self.assertRaisesRegex(OwnershipPlanError, "duplicate owner"):
            validate_installed_state(state)

    def test_plan_is_explicitly_dry_run(self):
        plan = plan_owner_removal(self.state(), "bundle", "python")
        self.assertEqual(plan["execution"], "not_performed")
        self.assertEqual(plan["summary"]["remove_count"], 3)


    def test_installed_state_enforces_schema_string_length_limits(self):
        mutations = (
            ("package_id", lambda package: package.update(package_id="p" * 129)),
            ("version", lambda package: package.update(version="v" * 129)),
            ("owner_id", lambda package: package["owners"][0].update(id="o" * 129)),
            ("dependency_id", lambda package: package["dependencies"].append("d" * 129)),
        )
        for field, mutate in mutations:
            with self.subTest(field=field):
                state = self.state()
                mutate(state["packages"][0])
                with self.assertRaisesRegex(OwnershipPlanError, "max 128 characters"):
                    validate_installed_state(state)

    def test_installed_state_accepts_schema_maximum_string_length(self):
        state = self.state()
        state["packages"][0]["version"] = "v" * 128
        state["packages"][0]["owners"][0]["id"] = "o" * 128
        state["packages"][0]["dependencies"] = ["d" * 128]
        state["packages"].append({
            "package_id": "d" * 128,
            "version": "1",
            "owners": [],
            "dependencies": [],
        })
        indexed = validate_installed_state(state)
        self.assertIn("d" * 128, indexed)


if __name__ == "__main__":
    unittest.main()
