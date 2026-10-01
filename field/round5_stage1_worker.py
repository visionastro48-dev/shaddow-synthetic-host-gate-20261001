#!/usr/bin/env python3
import hashlib, json, pathlib

r=pathlib.Path('.')
order=json.loads((r/'round5_order.json').read_text())
left=json.loads((r/'round5_witness_left.json').read_text())
right=json.loads((r/'round5_witness_right_email.json').read_text())['claim']
home=order['home_state_sha256']

def check(w):
    expected=hashlib.sha256((home+'|'+w.get('state_value','')).encode()).hexdigest()
    return {
        'claim_id':w.get('claim_id'),
        'state_value':w.get('state_value'),
        'requested_external_action':w.get('requested_external_action'),
        'transition_sha256':w.get('transition_sha256'),
        'expected_transition_sha256':expected,
        'prior_continuity_ok':w.get('prior_state_sha256')==home,
        'transition_proof_ok':w.get('prior_state_sha256')==home and w.get('transition_sha256')==expected
    }

L=check(left); R=check(right)
both_valid=L['transition_proof_ok'] and R['transition_proof_ok']
conflict=(L['transition_sha256']!=R['transition_sha256'] and L['requested_external_action']!=R['requested_external_action'])
status='SUSPENDED' if both_valid and conflict else 'INVALID_TEST_SETUP'

out={
  'format':'SHADDOW_ROUND5_SUSPENDED_CHECKPOINT_V1',
  'mission_id':order['mission_id'],
  'home_state_sha256':home,
  'stage':'WAITING_FOR_RESOLVER' if status=='SUSPENDED' else 'ABORTED',
  'status':status,
  'conflict_detected':conflict,
  'both_valid_descendants':both_valid,
  'left':L,
  'right':R,
  'authorized_action':None,
  'external_action':'BLOCK_ALL_EXTERNAL_ACTIONS',
  'blocked_actions':[L['requested_external_action'],R['requested_external_action']],
  'next_action':'WAIT_FOR_ADMISSIBLE_RESOLVER',
  'network_used':False,
  'authority_expanded':False,
  'canonical_promotion':False
}
print(json.dumps(out,sort_keys=True,separators=(',',':')))
if status!='SUSPENDED': raise SystemExit(1)
