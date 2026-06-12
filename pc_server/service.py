"""Core PC-side service composition without socket or dashboard code."""

import traceback

from classifier_adapter import SleepClassifierAdapter
from comfort_policy import decide_control_command, initial_policy_state
from protocol import (
    CONTROL_COMMAND,
    CONTROL_STATUS,
    SENSOR_DATA,
    SLEEP_RESULT,
    build_no_action_command,
    validate_message,
)
from state_store import AppState, MODE_MANUAL


class SleepMonitorPcService(object):
    """Compose protocol, classifier, policy, state, and storage for one client."""

    def __init__(
        self,
        classifier_adapter=None,
        app_state=None,
        storage=None,
        policy_decider=None,
        policy_state=None,
    ):
        self.classifier_adapter = classifier_adapter or SleepClassifierAdapter()
        self.app_state = app_state or AppState()
        self.storage = storage
        self.policy_decider = policy_decider or decide_control_command
        self.policy_state = policy_state or initial_policy_state()
        self.last_error = None

    def process_sensor_data(self, sensor_data, now_s=None):
        """Process one board-originated sample.

        Returns a dictionary containing the two messages that must be sent back
        to PYNQ in order: ``sleep_result`` followed by ``control_command``.
        """
        validate_message(sensor_data, expected_type=SENSOR_DATA)
        self._append_storage(sensor_data)

        sleep_result = self.classifier_adapter.classify(sensor_data)
        validate_message(sleep_result, expected_type=SLEEP_RESULT)

        control_command = self._build_control_command(
            sensor_data,
            sleep_result,
            now_s=now_s,
        )
        validate_message(control_command, expected_type=CONTROL_COMMAND)

        self._append_storage(sleep_result)
        self._append_storage(control_command)
        self.app_state.record_sensor_cycle(
            sensor_data,
            sleep_result,
            control_command,
        )
        return {
            "sleep_result": sleep_result,
            "control_command": control_command,
        }

    def process_control_status(self, control_status):
        """Record one PYNQ execution result."""
        validate_message(control_status, expected_type=CONTROL_STATUS)
        self._append_storage(control_status)
        self.app_state.record_control_status(control_status)
        return control_status

    def set_active_client(self, address):
        self.app_state.set_active_client(address)

    def clear_active_client(self, address=None):
        return self.app_state.clear_active_client(address)

    def set_control_mode(self, mode):
        self.app_state.set_control_mode(mode)

    def queue_manual_command(self, command):
        return self.app_state.queue_manual_command(command)

    def snapshot(self):
        return self.app_state.snapshot()

    def _build_control_command(self, sensor_data, sleep_result, now_s=None):
        snapshot = self.app_state.snapshot()
        mode = snapshot["control_mode"]
        pending_manual = None
        if mode == MODE_MANUAL:
            pending_manual = self.app_state.take_pending_manual_command()

        try:
            command, next_policy_state = self.policy_decider(
                sensor_data,
                sleep_result,
                policy_state=self.policy_state,
                mode=mode,
                pending_manual_command=pending_manual,
                now_s=now_s,
            )
            self.policy_state = next_policy_state
            self.last_error = None
            return command
        except Exception as exc:
            self.last_error = traceback.format_exc(limit=4)
            return build_no_action_command(
                sensor_data.get("sample_id", sleep_result.get("sample_id", -1)),
                mode=mode,
                reason="policy_error:{0}".format(type(exc).__name__),
            )

    def _append_storage(self, message):
        if self.storage is None:
            return
        self.storage.append_record(message)
