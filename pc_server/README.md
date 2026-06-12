# pc_server

PC-side socket service, sleep classification, comfort policy, persistent
storage, and dashboard entry point for the final software integration phase.

The original socket/Excel files came from
`handoff/sleep_socket_project/sleep_socket_project/` and should be treated as
idea-level reference code, not as final architecture constraints.

## Files

| File | Purpose |
|---|---|
| [protocol_config.py](protocol_config.py) | Socket, Excel, field, and state-code configuration. |
| [excel_utils.py](excel_utils.py) | Legacy Excel workbook helper; may become a storage implementation detail. |
| [sleep_classifier.py](sleep_classifier.py) | Pure-Python DREAMT GRU classifier that loads `sleep_model.bin` and emits `sleep_result`. |
| [sleep_model.bin](sleep_model.bin) | Lightweight classifier weights used by `sleep_classifier.py`. |
| [dashboard_server.py](dashboard_server.py) | Current PC dashboard/service prototype and intended final PC entry after refactor. |
| [protocol.py](protocol.py) | Canonical newline JSON protocol helpers and validation for four message types. |
| [protocol_selftest.py](protocol_selftest.py) | Dependency-free SW-0 protocol self-test. |
| [comfort_policy.py](comfort_policy.py) | Pure first-version comfort policy that emits validated `control_command` messages. |
| [comfort_policy_selftest.py](comfort_policy_selftest.py) | Dependency-free SW-1 policy self-test. |
| [state_store.py](state_store.py) | Thread-safe `AppState` for single-client dashboard/service state and pending manual commands. |
| [storage.py](storage.py) | JSONL four-record storage backend for `sensor_data`, `sleep_result`, `control_command`, and `control_status`. |
| [state_storage_selftest.py](state_storage_selftest.py) | Dependency-free SW-2 AppState/storage self-test. |
| [pc_server.py](pc_server.py) | Legacy/minimal socket smoke; not the final acceptance entry. |
| [fake_pynq_client.py](fake_pynq_client.py) | To be rewritten as the new-protocol PC-only validation client. |

Remaining planned first-version modules:

| File | Purpose |
|---|---|
| `classifier_adapter.py` | Stable wrapper around `sleep_classifier.py` and future model implementations. |
| `service.py` | Single-client TCP service that composes protocol, classifier, policy, state, and storage. |
| `static/` | Dashboard HTML/CSS/JS split out of `dashboard_server.py`. |

## Run Order

Install the PC dependency:

```bash
pip install -r requirements.txt
```

Planned final PC entry:

```bash
python dashboard_server.py
```

Legacy PC-local smoke:

```bash
python pc_server.py
python fake_pynq_client.py
```

Protocol self-test:

```bash
python protocol_selftest.py
```

Comfort policy self-test:

```bash
python comfort_policy_selftest.py
```

State/storage self-test:

```bash
python state_storage_selftest.py
```

For real PYNQ integration, the board client must connect to the PC's real IPv4
address, not `127.0.0.1`.

## Protocol Direction

For each board-originated `sensor_data`, the final PC service sends exactly two
newline JSON messages in order:

```text
sleep_result
control_command
```

The PYNQ client then replies with:

```text
control_status
```

Manual dashboard controls set a pending real device command and wait for the
next `sensor_data`; they do not bypass the main socket loop. AC commands are
one-shot IR actions. Humidifier control is a target state. Desired-state UI can
be added later, but first version must not automatically replay AC desired
state.

See [../docs/protocol.md](../docs/protocol.md) and
[../docs/software_integration_plan.md](../docs/software_integration_plan.md).
