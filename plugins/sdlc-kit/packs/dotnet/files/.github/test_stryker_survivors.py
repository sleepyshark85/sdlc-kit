"""Tests for stryker_survivors.py. Run with `python3 -m unittest discover -s .github`."""
import importlib.util
import os
import unittest

spec = importlib.util.spec_from_file_location(
    "stryker_survivors", os.path.join(os.path.dirname(os.path.abspath(__file__)), "stryker_survivors.py"))
survivors = importlib.util.module_from_spec(spec)
spec.loader.exec_module(survivors)


def mutant(status, line, mutator="Equality"):
    return {"status": status, "mutatorName": mutator, "location": {"start": {"line": line, "column": 1}}}


class SurvivorsTest(unittest.TestCase):
    def test_only_survived_and_uncovered_mutants_are_listed_in_order(self):
        report = {"files": {
            "src/B.cs": {"mutants": [mutant("Killed", 3), mutant("NoCoverage", 9, "Block")]},
            "src/A.cs": {"mutants": [mutant("Survived", 7), mutant("Timeout", 2), mutant("CompileError", 4)]},
        }}

        self.assertEqual([("src/A.cs", 7, "Equality", "Survived"), ("src/B.cs", 9, "Block", "NoCoverage")],
                         survivors.survivors(report))

    def test_the_table_names_each_survivor(self):
        self.assertEqual("1 surviving mutants:\n\n| File | Line | Mutator | Status |\n|---|---|---|---|\n"
                         "| src/A.cs | 7 | Equality | Survived |\n",
                         survivors.table([("src/A.cs", 7, "Equality", "Survived")], "/repo"))

    def test_no_survivors_says_so(self):
        self.assertEqual("No surviving mutants.\n", survivors.table([], "/repo"))


if __name__ == "__main__":
    unittest.main()
