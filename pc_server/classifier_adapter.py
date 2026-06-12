"""Stable adapter around the current sleep classifier implementation."""

from protocol import SLEEP_RESULT, ProtocolError, now_text, validate_message


DEFAULT_CLASSIFIER_ID = "dreamt_gru_v1"


class SleepClassifierAdapter(object):
    """Validate sensor input and normalize classifier ``sleep_result`` output."""

    def __init__(self, classifier=None, classifier_id=DEFAULT_CLASSIFIER_ID):
        self._classifier = classifier
        self.classifier_id = classifier_id
        self.last_error = None

    def classify(self, sensor_data):
        try:
            validate_message(sensor_data, expected_type="sensor_data")
        except ProtocolError as exc:
            self.last_error = str(exc)
            sample_id = _sample_id(sensor_data)
            return self._invalid_result(sample_id, "classifier_input_invalid")

        sample_id = _sample_id(sensor_data)
        try:
            classifier = self._resolve_classifier()
            raw_result = classifier(sensor_data)
            result = self._normalize_result(raw_result, sample_id)
            validate_message(result, expected_type=SLEEP_RESULT)
            self.last_error = None
            return result
        except Exception as exc:
            self.last_error = "{0}: {1}".format(type(exc).__name__, exc)
            return self._invalid_result(sample_id, "classifier_error")

    def _resolve_classifier(self):
        if self._classifier is None:
            from sleep_classifier import classify_sleep_state

            self._classifier = classify_sleep_state
        return self._classifier

    def _normalize_result(self, raw_result, sample_id):
        if not isinstance(raw_result, dict):
            raise ProtocolError("classifier result must be an object")
        result = dict(raw_result)
        result["type"] = SLEEP_RESULT
        result["timestamp"] = result.get("timestamp") or now_text()
        result["sample_id"] = sample_id
        result["remark"] = result.get("remark") or self.classifier_id
        result["state_valid"] = result.get("state_valid", 0)
        return result

    def _invalid_result(self, sample_id, reason):
        remark = reason
        if self.last_error:
            remark = "{0}:{1}".format(reason, _short_error(self.last_error))
        result = {
            "type": SLEEP_RESULT,
            "timestamp": now_text(),
            "sample_id": sample_id,
            "sleep_state_code": 0,
            "state_valid": 0,
            "remark": remark,
        }
        validate_message(result, expected_type=SLEEP_RESULT)
        return result


def classify_sensor_data(sensor_data, adapter=None):
    """Convenience helper for callers that do not need adapter state."""
    active_adapter = adapter or SleepClassifierAdapter()
    return active_adapter.classify(sensor_data)


def _sample_id(sensor_data):
    if isinstance(sensor_data, dict):
        try:
            return int(sensor_data.get("sample_id", -1))
        except (TypeError, ValueError):
            return -1
    return -1


def _short_error(text, limit=96):
    text = str(text).replace("\n", " ")
    return text[:limit]
