import time


from tests.conftest import domain_url


def test_audit_log(clean_db, http_client):
    time.sleep(0.25)

    # create object
    obj = {
        '_meta': {
            'note': 'test note please ignore'
        },
        'name': 'test',
        'description': 'data data data',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/dataset', json=obj)
    assert response.status_code == 201, response.text
    dataset_key = response.json()['_key']

    time.sleep(0.25)

    # update object
    partial = {
        'name': 'test updated'
    }
    response = http_client.patch(f'{domain_url}/infoflow/api/dataset/{dataset_key}', json=partial)
    assert response.status_code == 200, response.text

    time.sleep(0.25)

    # update object
    partial = {
        'name': 'test updated again'
    }
    response = http_client.patch(f'{domain_url}/infoflow/api/dataset/{dataset_key}', json=partial)
    assert response.status_code == 200, response.text

    time.sleep(0.25)

    # delete object
    response = http_client.delete(f'{domain_url}/infoflow/api/dataset/{dataset_key}')
    assert response.status_code == 204, response.text

    time.sleep(0.25)

    # get audit log
    response = http_client.get(f'{domain_url}/system/api/audit_log/grouping/{dataset_key}')
    assert response.status_code == 200, response.text
    results_total = response.json().get('results_total')
    results = response.json().get('results')

    assert results_total == 4
    assert len(results) == 4
    assert results[0]['operation'] == 'create'
    assert results[0]['edge'] is False
    assert results[0]['note'] == 'test note please ignore'

    assert results[1]['operation'] == 'update'
    assert results[1]['edge'] is False
    assert results[1]['note'] is None

    assert results[2]['operation'] == 'update'
    assert results[2]['edge'] is False
    assert results[2]['note'] is None

    assert results[3]['operation'] == 'delete'
    assert results[3]['edge'] is False
    assert results[3]['note'] is None

    time.sleep(0.25)

    # create related object
    obj = {
        'content': 'testing testing',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/comment', json=obj)
    assert response.status_code == 201, response.text
    comment_key = response.json()['_key']

    time.sleep(0.25)

    # create related object
    data = {
        'from_class': 'comment',
        'from_key': comment_key,
        '_meta': {
            'note': 'still testing please ignore'
        }
    }

    response = http_client.post(f'{domain_url}/infoflow/api/dataset/{dataset_key}/comments', json=data)
    assert response.status_code == 201, response.text

    time.sleep(0.25)

    # update related object
    data = {
        'from_class': 'comment',
        'from_key': comment_key,
        'active': False
    }
    response = http_client.patch(f'{domain_url}/infoflow/api/dataset/{dataset_key}/comments', json=data)
    assert response.status_code == 204, response.text

    time.sleep(0.25)

    # update related object
    data = {
        'from_class': 'comment',
        'from_key': comment_key,
        'active': True
    }
    response = http_client.patch(f'{domain_url}/infoflow/api/dataset/{dataset_key}/comments', json=data)
    assert response.status_code == 204, response.text

    time.sleep(0.25)

    # delete related object
    data = {
        'from_class': 'comment',
        'from_key': comment_key,
    }
    response = http_client.delete(f'{domain_url}/infoflow/api/dataset/{dataset_key}/comments', params=data)
    assert response.status_code == 204, response.text

    time.sleep(0.25)

    # get audit log (no edges)
    response = http_client.get(f'{domain_url}/system/api/audit_log/grouping/{dataset_key}')
    assert response.status_code == 200, response.text
    results_total = response.json().get('results_total')
    results = response.json().get('results')
    assert results_total == 4
    assert len(results) == 4

    # get audit log (with edges)
    response = http_client.get(f'{domain_url}/system/api/audit_log/grouping/{dataset_key}?edges=true')
    assert response.status_code == 200, response.text
    results_total = response.json().get('results_total')
    results = response.json().get('results')

    assert results_total == 8
    assert len(results) == 8
    assert results[4]['operation'] == 'create'
    assert results[4]['from_id'] == f'comment/{comment_key}'
    assert results[4]['to_id'] == f'grouping/{dataset_key}'
    assert results[4]['edge'] is True
    assert results[4]['note'] == 'still testing please ignore'

    assert results[5]['operation'] == 'update'
    assert results[5]['from_id'] == f'comment/{comment_key}'
    assert results[5]['to_id'] == f'grouping/{dataset_key}'
    assert results[5]['edge'] is True
    assert results[5]['note'] is None

    assert results[6]['operation'] == 'update'
    assert results[6]['from_id'] == f'comment/{comment_key}'
    assert results[6]['to_id'] == f'grouping/{dataset_key}'
    assert results[6]['edge'] is True
    assert results[6]['note'] is None

    assert results[7]['operation'] == 'delete'
    assert results[7]['from_id'] == f'comment/{comment_key}'
    assert results[7]['to_id'] == f'grouping/{dataset_key}'
    assert results[7]['edge'] is True
    assert results[7]['note'] is None


def test_audit_log_bulk(clean_db, http_client):
    obj = {
        'content': 'testing testing',
    }

    response = http_client.post(f'{domain_url}/infoflow/api/comment', json=obj)
    assert response.status_code == 201, response.text
    comment_key = response.json()['_key']

    audits = []
    for i in range(900):
        audits.append({
            'pre': {},
            'post': {
                '_id': f'comment/{comment_key}',
                'content': 'testing',
            },
        })

    response = http_client.post(f'{domain_url}/system/api/audit_log', json=audits)
    assert response.status_code == 201, response.text

    results = response.json()
    assert len(results) == 900
