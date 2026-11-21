from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'sample_data'
VERSION = 'gate-1.0.0'
PREVIEW = 'sample'
ZONE = 'Asia/Shanghai'
BYTE_LIMIT = 512 * 1024
ROW_LIMIT = 12_000
PAIR_MS = 900
RETURN_MS = 250
COLUMNS = {
    'pulses.csv': ('pulse', 'station', 'gate', 'beam', 'device_at', 'ticket', 'note'),
    'offsets.csv': ('station', 'gate', 'device_from', 'device_to', 'offset_ms'),
    'passes.csv': ('ticket', 'valid_from', 'valid_to', 'transfer'),
    'links.csv': ('from_station', 'to_station', 'min_seconds', 'max_seconds'),
}
