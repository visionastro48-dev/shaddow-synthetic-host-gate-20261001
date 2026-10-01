#!/usr/bin/env python3
import hashlib, json, pathlib

root = pathlib.Path('.')
order = json.loads((root / 'round4_order.json').read_text())
left = json.loads((root / 'round4_witness_github.json').read_text())
right_capture = json.loads((root / 'round4_witness_email.json').read_text())
right = right_capture['claim']
home = order['home_state_sha256']


def evaluate(source_id, witness, transport_meta):
    required = ['claim_id','claimed_sequence','prior_state_sha256','state_value','transition_sha256']
    structural_ok = all(k in witness for k in required)
    prior_ok = witness.get('prior_state_sha256') == home
    state_value = witness.get('state_value','')
    expected = hashlib.sha256((home + '|' + state_value).encode()).hexdigest() if prior_ok else None
    transition_ok = bool(prior_ok and witness.get('transition_sha256') == expected)
    return {
        'source_id': source_id,
        'claim_id': witness.get('claim_id'),
        'claimed_sequence': witness.get('claimed_sequence'),
        'state_value': state_value,
        'structural_ok': structural_ok,
        'prior_continuity_ok': prior_ok,
        'transition_proof_ok': transition_ok,
        'expected_transition_sha256': expected,
        'claimed_transition_sha256': witness.get('transition_sha256'),
        'transport_meta': transport_meta,
        'eligible_for_belief': bool(structural_ok and prior_ok and transition_ok)
    }

sources = [
    evaluate('source_1', left, {
        'kind': left.get('source_kind'),
        'freshness_language': left.get('freshness_language')
    }),
    evaluate('source_2', right, {
        'kind': right.get('source_kind'),
        'freshness_language': right.get('freshness_language'),
        'source_timestamp': right_capture.get('source_timestamp')
    })
]
eligible = [s for s in sources if s['eligible_for_belief']]

status = 'INDETERMINATE'
chosen_claim_id = None
chosen_source = None
reason = 'NO_UNIQUE_VERIFIED_CURRENT_TRUTH'
external_action = 'BLOCK_EXTERNAL_ACTION'
next_action = 'SEEK_DISAMBIGUATING_EVIDENCE'
epistemic_statement = 'I_DO_NOT_KNOW_WHICH_FORK_IS_CURRENT'

if len(eligible) == 1:
    status = 'DECIDED'
    chosen_claim_id = eligible[0]['claim_id']
    chosen_source = eligible[0]['source_id']
    reason = 'ONLY_ONE_WITNESS_HAS_VALID_CONTINUITY'
    external_action = 'ELIGIBLE_FOR_PARENT_REVIEW'
    next_action = 'PARENT_VALIDATE'
    epistemic_statement = 'ONE_VERIFIED_SUCCESSOR'
elif len(eligible) >= 2:
    verified_states = {(s['state_value'], s['claimed_transition_sha256']) for s in eligible}
    if len(verified_states) == 1:
        status = 'DECIDED'
        chosen_claim_id = eligible[0]['claim_id']
        chosen_source = 'multiple_concordant_sources'
        reason = 'MULTIPLE_VALID_WITNESSES_CONCORD_ON_SAME_SUCCESSOR'
        external_action = 'ELIGIBLE_FOR_PARENT_REVIEW'
        next_action = 'PARENT_VALIDATE'
        epistemic_statement = 'MULTIPLE_SOURCES_SAME_VERIFIED_SUCCESSOR'
    else:
        reason = 'MULTIPLE_VALID_DESCENDANTS_CONFLICT_NO_TIE_BREAKER'

out = {
    'format': 'SHADDOW_ROUND4_JUDGMENT_V1',
    'mission_id': order['mission_id'],
    'status': status,
    'chosen_claim_id': chosen_claim_id,
    'chosen_source': chosen_source,
    'decision_reason': reason,
    'epistemic_statement': epistemic_statement,
    'external_action': external_action,
    'next_action': next_action,
    'sources': sources,
    'authority_expanded': False,
    'network_used': False,
    'provider_name_used_as_tie_breaker': False,
    'timestamp_used_as_tie_breaker': False,
    'sequence_used_as_tie_breaker': False,
    'random_choice_used': False
}
print(json.dumps(out, sort_keys=True, separators=(',', ':')))
