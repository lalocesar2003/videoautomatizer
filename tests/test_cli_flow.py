import sys
import unittest
from unittest.mock import patch

import main


class CliFlowTests(unittest.TestCase):
    def test_run_all_executes_full_pipeline_in_order(self) -> None:
        calls = []

        with (
            patch.object(main, "run_parse", side_effect=lambda: calls.append("parse")),
            patch.object(main, "run_classify", side_effect=lambda: calls.append("classify")),
            patch.object(main, "run_search", side_effect=lambda: calls.append("search")),
            patch.object(main, "run_score", side_effect=lambda: calls.append("score")),
        ):
            main.run_all()

        self.assertEqual(calls, ["parse", "classify", "search", "score"])

    def test_main_all_command_uses_run_all(self) -> None:
        with (
            patch.object(sys, "argv", ["main.py", "all"]),
            patch.object(main, "run_all") as run_all,
        ):
            main.main()

        run_all.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
