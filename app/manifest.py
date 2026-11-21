import hashlib
import json
from datetime import UTC, datetime

from app.problems import Problem
from app.settings import COLUMNS, PAIR_MS, RETURN_MS, VERSION, ZONE


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def describe(files):
    if set(files) != set(COLUMNS):
        raise Problem('FILE_SET', detail={'expected': list(COLUMNS)})
    return [{'source': name, 'bytes': len(files[name]), 'sha256': sha(files[name])} for name in COLUMNS]


def fingerprint(inputs):
    return 'gate_' + sha(json_bytes([VERSION, PAIR_MS, RETURN_MS, ZONE, inputs]))[:24]


def run_manifest(run_id, inputs, elapsed_ms):
    return {'run_id': run_id, 'version': VERSION, 'generated_at': datetime.now(UTC).isoformat(timespec='seconds'),
            'duration_ms': elapsed_ms, 'inputs': inputs, 'time_zone': ZONE,
            'parameters': {'pair_ms': PAIR_MS, 'return_ms': RETURN_MS, 'shift_hours': [6, 14, 22]}}
