import json
import logging

from agrofarm_api.middleware.logging import JsonFormatter


def test_json_formatter_outputs_request_id_and_message() -> None:
    record = logging.LogRecord('x', logging.INFO, __file__, 1, 'hello %s', ('world',), None)
    record.request_id = 'rid-1'
    payload = json.loads(JsonFormatter().format(record))
    assert payload['message'] == 'hello world'
    assert payload['request_id'] == 'rid-1'
    assert payload['severity'] == 'INFO'


def test_json_formatter_defaults_request_id() -> None:
    record = logging.LogRecord('x', logging.WARNING, __file__, 1, 'm', (), None)
    payload = json.loads(JsonFormatter().format(record))
    assert payload['request_id'] == '-'
