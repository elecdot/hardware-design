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
| [classifier_adapter.py](classifier_adapter.py) | Stable wrapper around `sleep_classifier.py` with validated `sleep_result` output and failure fallback. |
| [classifier_adapter_selftest.py](classifier_adapter_selftest.py) | Dependency-free classifier adapter self-test using fake classifier functions. |
| [sleep_classifier_selftest.py](sleep_classifier_selftest.py) | Classifier warm-up regression for JY901-only invalid samples and true HR/SpO2 invalid samples. |
| [comfort_policy.py](comfort_policy.py) | Pure first-version comfort policy that emits validated `control_command` messages. |
| [comfort_policy_selftest.py](comfort_policy_selftest.py) | Dependency-free SW-1 policy self-test. |
| [state_store.py](state_store.py) | Thread-safe `AppState` for single-client dashboard/service state and pending manual commands. |
| [storage.py](storage.py) | JSONL four-record storage backend for `sensor_data`, `sleep_result`, `control_command`, and `control_status`. |
| [state_storage_selftest.py](state_storage_selftest.py) | Dependency-free SW-2 AppState/storage self-test. |
| [service.py](service.py) | Socket-free PC service composition for one `sensor_data` cycle and `control_status` recording. |
| [service_selftest.py](service_selftest.py) | Dependency-free service composition self-test. |
| [socket_service.py](socket_service.py) | Minimal sequential TCP loop for the new four-message protocol. |
| [socket_service_selftest.py](socket_service_selftest.py) | Loopback TCP self-test for `sensor_data -> sleep_result/control_command -> control_status`. |
| [pc_server.py](pc_server.py) | Legacy/minimal socket smoke; not the final acceptance entry. |
| [fake_pynq_client.py](fake_pynq_client.py) | New-protocol PC-only fake PYNQ client. |
| [fake_pynq_client_selftest.py](fake_pynq_client_selftest.py) | Loopback self-test for fake client plus minimal socket service. |

Remaining planned first-version modules:

| File | Purpose |
|---|---|
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

Minimal new-protocol socket service:

```bash
python socket_service.py --host 0.0.0.0 --port 9000
```

Legacy PC-local smoke:

```bash
python pc_server.py
python fake_pynq_client.py
```

New-protocol PC-only smoke:

```bash
python socket_service.py --host 127.0.0.1 --port 9000
python fake_pynq_client.py --host 127.0.0.1 --port 9000 --samples 5 --interval 1.0
```

Protocol self-test:

```bash
python protocol_selftest.py
```

Classifier adapter self-test:

```bash
python classifier_adapter_selftest.py
```

Classifier warm-up/JY901 robustness self-test:

```bash
python sleep_classifier_selftest.py
```

Comfort policy self-test:

```bash
python comfort_policy_selftest.py
```

State/storage self-test:

```bash
python state_storage_selftest.py
```

Service composition self-test:

```bash
python service_selftest.py
```

Socket loopback self-test:

```bash
python socket_service_selftest.py
```

Fake PYNQ client self-test:

```bash
python fake_pynq_client_selftest.py
```

For real PYNQ integration, the board client must connect to the PC's real IPv4
address, not `127.0.0.1`.

Use [../docs/software_integration_runbook.md](../docs/software_integration_runbook.md)
for the full PC/PYNQ integration sequence, including PYNQ file deployment,
dry-run socket smoke, real board client run, and evidence capture.

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
