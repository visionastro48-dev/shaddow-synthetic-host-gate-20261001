#!/usr/bin/env python3
import hashlib, json, pathlib, sys

order = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
target_path = pathlib.Path(sys.argv[2])
data = target_path.read_bytes()
target = json.loads(data.decode('utf-8'))
if target.get('format') != 'SHADDOW_FIELD_TARGET_V1':
    raise SystemExit('target format rejected')
result = {
    'format': 'SHADDOW_FIELD_RESULT_V2',
    'mission_id': order['mission_id'],
    'worker_generation': order['worker_generation'],
    'target_sha256': hashlib.sha256(data).hexdigest(),
    'target_size_bytes': len(data),
    'observed_version': target.get('version'),
    'observed_objective_state': target.get('objective_state'),
    'status': 'PASS',
    'authority_claims': {
        'network_used': False,
        'repository_write_used': False,
        'publication_used': False,
        'private_parent_state_used': False
    }
}
print(json.dumps(result, sort_keys=True, separators=(',', ':')))
