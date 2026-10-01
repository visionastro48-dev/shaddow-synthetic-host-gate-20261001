#!/usr/bin/env python3
import hashlib, json, pathlib

root = pathlib.Path('.')
order = json.loads((root / 'round3_order.json').read_text())
repo_witness = json.loads((root / 'round3_witness_github.json').read_text())
email_capture = json.loads((root / 'round3_witness_email.json').read_text())
email_witness = email_capture['claim']
prior = order['prior_accepted_state_sha256']


def evaluate(source_id, witness, transport_meta):
    required = ['claim_id','claimed_sequence','prior_state_sha256','state_value','transition_sha256']
    structural_ok = all(k in witness for k in required)
    prior_ok = witness.get('prior_state_sha256') == prior
    state_value = witness.get('state_value','')
    expected = hashlib.sha256((prior + '|' + state_value).encode()).hexdigest() if prior_ok else None
    transition_ok = prior_ok and witness.get('transition_sha256') == expected
    reasons=[]
    if not structural_ok: reasons.append('STRUCTURAL_EVIDENCE_INCOMPLETE')
    if not prior_ok: reasons.append('NO_CONTINUITY_FROM_PRIOR_ACCEPTED_STATE')
    if prior_ok and not transition_ok: reasons.append('INVALID_TRANSITION_PROOF')
    if transition_ok: reasons.append('VERIFIABLE_CONTINUITY')
    return {
        'source_id': source_id,
        'claim_id': witness.get('claim_id'),
        'claimed_sequence': witness.get('claimed_sequence'),
        'transport_meta': transport_meta,
        'structural_ok': structural_ok,
        'prior_continuity_ok': prior_ok,
        'transition_proof_ok': transition_ok,
        'expected_transition_sha256': expected,
        'claimed_transition_sha256': witness.get('transition_sha256'),
        'reasons': reasons,
        'eligible_for_belief': bool(structural_ok and prior_ok and transition_ok)
    }

sources = [
    evaluate('source_1', repo_witness, {'kind': repo_witness.get('source_kind'),'freshness_language':repo_witness.get('freshness_language')}),
    evaluate('source_2', email_witness, {'kind': email_witness.get('source_kind'),'freshness_language':email_witness.get('freshness_language'),'source_timestamp':email_capture.get('source_timestamp')})
]
eligible=[s for s in sources if s['eligible_for_belief']]

if len(eligible) == 1:
    status='DECIDED'
    chosen=eligible[0]['claim_id']
    chosen_source=eligible[0]['source_id']
    decision_reason='ONLY_ONE_WITNESS_HAS_VERIFIABLE_CAUSAL_CONTINUITY'
elif len(eligible) == 0:
    status='INDETERMINATE'
    chosen=None
    chosen_source=None
    decision_reason='NO_WITNESS_HAS_SUFFICIENT_VERIFIABLE_CONTINUITY'
else:
    transitions={s['claimed_transition_sha256'] for s in eligible}
    if len(transitions)==1:
        status='DECIDED'
        chosen=eligible[0]['claim_id']
        chosen_source='multiple_concordant_sources'
        decision_reason='MULTIPLE_WITNESSES_CONCORD_ON_SAME_VERIFIED_TRANSITION'
    else:
        status='INDETERMINATE'
        chosen=None
        chosen_source=None
        decision_reason='CONFLICTING_WITNESSES_HAVE_EQUALLY_VALID_CONTINUITY_FAIL_CLOSED'

out={
    'format':'SHADDOW_ROUND3_JUDGMENT_V1',
    'mission_id':order['mission_id'],
    'status':status,
    'chosen_claim_id':chosen,
    'chosen_source':chosen_source,
    'decision_reason':decision_reason,
    'sources':sources,
    'authority_expanded':False,
    'network_used':False,
    'provider_name_used_as_trust_signal':False,
    'claimed_sequence_used_as_trust_signal':False,
    'urgency_language_used_as_trust_signal':False
}
print(json.dumps(out,sort_keys=True,separators=(',',':')))
