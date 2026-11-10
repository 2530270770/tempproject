# -*- coding: utf-8 -*-
import unittest

from src.traceability.permissions import PermissionDenied, authorize
from src.traceability.state_machines import (
    CheckTaskMachine,
    EntryMachine,
    InvalidTransition,
    RegressionMachine,
)


class StateMachineTests(unittest.TestCase):
    def test_check_task_reaches_archive_in_order(self):
        machine = CheckTaskMachine()
        for event in ("PARSE", "CHECK", "REPORT", "CONFIRM", "ARCHIVE"):
            machine.trigger(event)
        self.assertEqual("已归档", machine.state)
        self.assertEqual(5, len(machine.history))

    def test_invalid_transition_is_rejected(self):
        machine = CheckTaskMachine()
        with self.assertRaises(InvalidTransition):
            machine.trigger("ARCHIVE")

    def test_entry_states_cover_and_change(self):
        machine = EntryMachine()
        for event in ("BASELINE", "COVER", "CHANGE"):
            machine.trigger(event)
        self.assertEqual("变更", machine.state)

    def test_regression_machine_closes(self):
        machine = RegressionMachine()
        for event in ("DETECT_CHANGE", "ANALYZE", "CLOSE"):
            machine.trigger(event)
        self.assertEqual("回归完成", machine.state)


class PermissionTests(unittest.TestCase):
    def test_student_cannot_check_other_team(self):
        with self.assertRaises(PermissionDenied):
            authorize("student", "run_check", caller_team="T01", target_team="T02")

    def test_student_cannot_check_own_team(self):
        with self.assertRaises(PermissionDenied):
            authorize("student", "run_check", caller_team="T01", target_team="T01")

    def test_student_can_view_own_team_only(self):
        authorize(
            "student",
            "view_current_team",
            caller_team="T01",
            target_team="T01",
        )
        with self.assertRaises(PermissionDenied):
            authorize(
                "student",
                "view_current_team",
                caller_team="T01",
                target_team="T02",
            )

    def test_student_cannot_confirm(self):
        with self.assertRaises(PermissionDenied):
            authorize("student", "confirm")

    def test_ta_cannot_change_configuration(self):
        with self.assertRaises(PermissionDenied):
            authorize("ta", "configure")

    def test_teacher_can_confirm(self):
        authorize("teacher", "confirm")


if __name__ == "__main__":
    unittest.main()
