# pc_server

PC-side socket, Excel logging, and rule-based sleep classification demo
migrated from `handoff/sleep_socket_project/sleep_socket_project/`.

## Files

| File | Purpose |
|---|---|
| [protocol_config.py](protocol_config.py) | Socket, Excel, field, and state-code configuration. |
| [excel_utils.py](excel_utils.py) | Excel workbook creation and append helpers. |
| [sleep_classifier.py](sleep_classifier.py) | Rule-based placeholder sleep classifier. |
| [pc_server.py](pc_server.py) | TCP server that receives `sensor_data`, logs Excel rows, and returns `sleep_result`. |
| [fake_pynq_client.py](fake_pynq_client.py) | PC-local fake client for socket/Excel validation. |

## Run Order

Install the PC dependency:

```bash
pip install -r requirements.txt
```

PC-local validation:

```bash
python pc_server.py
python fake_pynq_client.py
```

For real PYNQ integration, the board client must connect to the PC's real IPv4
address, not `127.0.0.1`.
