#!/usr/bin/env python3
import hashlib,json,pathlib
r=pathlib.Path('.')
cp_path=r/'round5_suspended_checkpoint.json'
cp=json.loads(cp_path.read_text())
resolver_cap=json.loads((r/'round5_resolver_slack.json').read_text())
res=resolver_cap['captured_statement']
cp_sha=hashlib.sha256(cp_path.read_bytes()).hexdigest()
errors=[]
if cp.get('status')!='SUSPENDED': errors.append('checkpoint_not_suspended')
if cp.get('stage')!='WAITING_FOR_RESOLVER': errors.append('checkpoint_wrong_stage')
if cp.get('authorized_action') is not None: errors.append('checkpoint_already_authorized')
if cp.get('external_action')!='BLOCK_ALL_EXTERNAL_ACTIONS': errors.append('checkpoint_not_fail_closed')
if res.get('mission_id')!=cp.get('mission_id'): errors.append('resolver_wrong_mission')
if res.get('checkpoint_sha256')!=cp_sha: errors.append('resolver_not_bound_to_exact_checkpoint')
claims={cp['left']['claim_id']:cp['left'],cp['right']['claim_id']:cp['right']}
winner=claims.get(res.get('winner_claim_id'))
loser=claims.get(res.get('loser_claim_id'))
if winner is None: errors.append('winner_not_in_checkpoint')
if loser is None: errors.append('loser_not_in_checkpoint')
if winner is not None and loser is not None and winner['claim_id']==loser['claim_id']: errors.append('winner_equals_loser')
if winner is not None and res.get('winner_transition_sha256')!=winner.get('transition_sha256'): errors.append('winner_transition_mismatch')
if winner is not None and res.get('authorized_action')!=winner.get('requested_external_action'): errors.append('resolver_action_not_bound_to_winner')
expected_resolver=hashlib.sha256((res.get('checkpoint_sha256','')+'|'+res.get('winner_claim_id','')+'|'+res.get('winner_transition_sha256','')+'|'+res.get('authorized_action','')).encode()).hexdigest()
if res.get('resolver_sha256')!=expected_resolver: errors.append('resolver_proof_invalid')
if winner is not None and not winner.get('transition_proof_ok'): errors.append('winner_was_not_valid_stage1_descendant')
if loser is not None and not loser.get('transition_proof_ok'): errors.append('loser_was_not_valid_stage1_descendant')

out={
  'format':'SHADDOW_ROUND5_RESUMED_AUTHORIZATION_V1',
  'mission_id':cp.get('mission_id'),
  'status':'RESOLVED_READY_FOR_PARENT_EFFECT' if not errors else 'FAIL_CLOSED',
  'resumed_from_checkpoint_sha256':cp_sha,
  'fresh_executor':True,
  'winner_claim_id':winner.get('claim_id') if winner and not errors else None,
  'loser_claim_id':loser.get('claim_id') if loser and not errors else None,
  'authorized_action':winner.get('requested_external_action') if winner and not errors else None,
  'blocked_action':loser.get('requested_external_action') if loser and not errors else None,
  'resolver_sha256':res.get('resolver_sha256'),
  'resolver_valid':not errors,
  'external_effect_authority':'PARENT_ONLY',
  'worker_executed_external_effect':False,
  'network_used':False,
  'authority_expanded':False,
  'canonical_promotion':False,
  'errors':errors
}
print(json.dumps(out,sort_keys=True,separators=(',',':')))
if errors: raise SystemExit(1)
