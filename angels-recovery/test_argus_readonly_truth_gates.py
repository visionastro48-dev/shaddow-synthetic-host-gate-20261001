import unittest
from argus_readonly_truth_gates import SOURCES, classify, collect


class FailClosed(unittest.TestCase):
    def test_edge_reachable_not_authority(self):
        status, ev = classify('edge', 200, dict(ok=True, schema='angels.shared-runtime/v1', writes=False))
        self.assertEqual(status, 'READONLY_COMPUTE_REACHABLE')
        self.assertIs(ev['production_authority'], False)

    def test_edge_writes_true_denied(self):
        self.assertEqual(classify('edge', 200, dict(ok=True, schema='angels.shared-runtime/v1', writes=True))[0], 'UNKNOWN_OR_INVALID')

    def test_readiness_hold_response_accepted_but_not_recovery(self):
        body=dict(ok=False, schema='angels.company-recovery-readiness/v1',
                  decision='HOLD_CANONICAL_WORKERS', production_authority_migrated=False,
                  resumed_real_worker_receipts_verified=False,
                  independent_single_writer_fencing_verified=False,
                  canonical_database_query_responded=False)
        outcome, ev = classify('readiness', 503, body)
        self.assertEqual(outcome, 'HOLD_CONFIRMED')
        self.assertIs(ev['production_authority'], False)

    def test_readiness_200_is_not_automatically_healthy(self):
        self.assertEqual(classify('readiness', 200, dict(ok=True))[0], 'UNKNOWN_OR_INVALID')

    def test_octopus_health_durable_truth_unavailable(self):
        body=dict(ok=True, service='octopus-public-proof', read_only=True,
                  durable_truth={'available': False}, source={'promoted': False})
        status, ev=classify('octopus', 200, body)
        self.assertEqual(status,'DURABLE_TRUTH_UNAVAILABLE')
        self.assertIs(ev['customers_or_payments_verified'],False)

    def test_octopus_promoted_source_invalid(self):
        body=dict(ok=True, service='octopus-public-proof', read_only=True,
                  durable_truth={'available': True}, source={'promoted': True})
        self.assertEqual(classify('octopus', 200, body)[0], 'UNKNOWN_OR_INVALID')

    def test_aether_disabled(self):
        status, ev=classify('aether',200,dict(ok=True,schema='aether.swarmmemo-webhook/v1',
                        event_actions_enabled=False,event_verification_ready=False))
        self.assertEqual(status,'EVENT_ACTIONS_DISABLED')
        self.assertIs(ev['event_verification_ready'], False)

    def test_aether_actions_enabled_does_not_grant(self):
        self.assertEqual(classify('aether',200,dict(ok=True,schema='aether.swarmmemo-webhook/v1',event_actions_enabled=True))[0],'UNKNOWN_OR_INVALID')

    def test_unknown_target_rejected(self):
        with self.assertRaises(ValueError): classify('unknown',200,{})

    def test_collect_four_probes_healthy_observation_still_hold(self):
        mapping={
            SOURCES['edge']:(200,dict(ok=True,schema='angels.shared-runtime/v1',writes=False)),
            SOURCES['readiness']:(503,dict(ok=False,schema='angels.company-recovery-readiness/v1',
                                  decision='HOLD_CANONICAL_WORKERS',production_authority_migrated=False,
                                  resumed_real_worker_receipts_verified=False,independent_single_writer_fencing_verified=False)),
            SOURCES['octopus']:(200,dict(ok=True,service='octopus-public-proof',read_only=True,
                                  durable_truth={'available':False},source={'promoted':False})),
            SOURCES['aether']:(200,dict(ok=True,schema='aether.swarmmemo-webhook/v1',event_actions_enabled=False))
        }
        r=collect(lambda url:mapping[url])
        self.assertEqual(r['observer_result'],'OBSERVATION_PASS')
        self.assertIs(r['company_execution_certified'],False)
        self.assertIs(r['external_effects_enabled'],False)

    def test_collect_probe_failure_fails_closed(self):
        r=collect(lambda url: (_ for _ in ()).throw(TimeoutError('timeout')))
        self.assertEqual(r['observer_result'],'PARTIAL_UNKNOWN')
        self.assertTrue(all(row['classification']=='UNKNOWN_OR_INVALID' for row in r['gates'].values()))


if __name__=='__main__': unittest.main(verbosity=2)