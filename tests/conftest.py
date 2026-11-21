import csv
from io import StringIO

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.pipeline import calculate
from app.runs import sample_files
from app.settings import COLUMNS


@pytest.fixture
def files():
    return sample_files()


@pytest.fixture(scope='module')
def sample():
    return calculate('fixture', sample_files())


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / 'gate.sqlite3')) as session:
        yield session


@pytest.fixture
def upload(client):
    def send(files):
        return client.post('/api/runs', files=[('files', (name, data, 'text/csv')) for name, data in files.items()])
    return send


@pytest.fixture
def csv_builder():
    def build(name, rows):
        stream = StringIO(newline='')
        writer = csv.writer(stream)
        writer.writerow(COLUMNS[name])
        writer.writerows(rows)
        return stream.getvalue().encode()
    return build


@pytest.fixture
def pulses():
    def build(entries):
        return [{'pulse': f'P{i}', 'beam': beam, 'corrected_ms': at, 'ticket': ticket, 'station': 'NTH', 'gate': 'G1',
                 'line': i + 2, 'offset_line': 2} for i, (beam, at, ticket) in enumerate(entries)]
    return build
