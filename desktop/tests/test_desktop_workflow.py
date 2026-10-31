from __future__ import annotations

import re
import unittest
from pathlib import Path


class DesktopWorkflowTests(unittest.TestCase):
    def test_push_validation_targets_the_current_nova_launch_branch(self) -> None:
        workflow = (
            Path(__file__).resolve().parents[2]
            / ".github"
            / "workflows"
            / "desktop-validation.yml"
        ).read_text(encoding="utf-8")
        match = re.search(
            r"(?ms)^  push:\n    branches:\n(?P<branches>(?:      - .+\n)+)",
            workflow,
        )
        self.assertIsNotNone(match, "desktop workflow must declare push branches")
        branches = re.findall(r"^      - (.+)$", match.group("branches"), re.MULTILINE)
        self.assertEqual(branches, ["02-NOVA"])


if __name__ == "__main__":
    unittest.main()
