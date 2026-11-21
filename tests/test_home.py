import re


def test_home_links_publish_rerun_anchor_and_attachment(client):
    html = client.get('/?run=sample').text
    assert all(term in html for term in ('进站轨', '出站轨', '脉冲证据', '运行回放', 'data-anchor="E-TR-IN-A"'))
    url = re.search('data-publish="([^"]+)"', html).group(1)
    first = client.post(url)
    assert first.status_code == 201 and first.json()['reused'] is False
    run_id = first.json()['run_id']
    html = client.get(f'/?run={run_id}').text
    rerun = client.post(re.search('data-publish="([^"]+/rerun)"', html).group(1))
    assert rerun.status_code == 200 and rerun.json()['reused'] is True
    assert rerun.json()['manifest'] == first.json()['manifest']
    export = re.search('href="([^"]+/export)"', html).group(1)
    assert client.get(export).content == client.get(export).content
    assert client.get(export).content.startswith(b'PK')


def test_all_module_endpoints_and_missing_run(client):
    totals = {'intake': 36, 'clock': 33, 'pairing': 17, 'direction': 17, 'transfer': 9, 'balance': 4, 'report': 4}
    for module, expected in totals.items():
        response = client.get(f'/api/{module}/sample')
        assert response.status_code == 200 and response.json()['total'] == expected
        unknown = client.get(f'/api/{module}/bad')
        assert (unknown.status_code, unknown.json()['code']) == (404, 'RUN_NOT_FOUND')


def test_invalid_view_is_explained_with_allowed_choices(client):
    response = client.get('/api/clock/sample', params={'view': 'no'})
    assert response.status_code == 422
    assert response.json()['detail']['allowed'] == ['main', 'versions', 'overlaps', 'isolated']


def test_missing_input_set_never_overwrites_current_run(client, files, upload):
    first = client.post('/api/runs/sample').json()['run_id']
    files.pop('links.csv')
    invalid = upload(files)
    assert (invalid.status_code, invalid.json()['code']) == (422, 'FILE_SET')
    assert f'data-run="{first}"' in client.get('/').text
