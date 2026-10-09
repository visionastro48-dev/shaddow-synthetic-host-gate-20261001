import datetime as dt
import unittest
from angels_foundation_30m_observer import audit,markdown,ENDPOINTS
UTC=dt.timezone.utc
NOW=dt.datetime(2026,10,9,9,0,tzinfo=UTC)
def sample():
    return {
        'supervisor':{'http':200,'body':{'status':'VALIDATED','source':'cron-5m','state_version':44,'state_updated_at':'2026-10-09T08:58:00Z','checks':[{'ok':True}]*4}},
        'hq':{'http':200,'body':{'ok':True,'canonical_company_control':'UNVERIFIED','hq_database':{'reachable':True},'production_authority_migrated':False}},
        'recovery':{'http':503,'body':{'decision':'HOLD_CANONICAL_WORKERS','production_authority_migrated':False,'canonical_database_query_responded':False}},
        'edge':{'http':200,'body':{'ok':True,'schema':'angels.shared-runtime/v1','writes':False}},
        'octopus':{'http':200,'body':{'ok':True,'durable_truth':{'available':False}}},
        'aether':{'http':200,'body':{'ok':True,'event_actions_enabled':False}}
    }
class TestReadOnly(unittest.TestCase):
    def check(self, p):return audit(p,NOW)
    def test_whitelist_exactly_6(self):self.assertEqual(len(ENDPOINTS),6)
    def test_green_readonly_remains_25_not_authorized(self):
        a=self.check(sample());self.assertTrue(a['supervisor_live']);self.assertTrue(a['original_production_hold_confirmed']);self.assertEqual(a['engineer_estimate_percent'],25);self.assertFalse(a['percent_certified']);self.assertFalse(a['authority_granted']);self.assertFalse(a['can_dispatch_work'])
    def test_supervisor_fails_if_stale(self):
        p=sample();p['supervisor']['body']['state_updated_at']='2026-10-09T06:00:00Z';self.assertFalse(self.check(p)['supervisor_live'])
    def test_supervisor_fails_if_any_check_fails(self):
        p=sample();p['supervisor']['body']['checks'][1]['ok']=False;self.assertFalse(self.check(p)['supervisor_live'])
    def test_supervisor_fails_if_missing_date(self):
        p=sample();p['supervisor']['body'].pop('state_updated_at');self.assertFalse(self.check(p)['supervisor_live'])
    def test_hq_unverified_authority_required(self):
        p=sample();p['hq']['body']['canonical_company_control']='MIGRATED';self.assertFalse(self.check(p)['independent_hq_readonly'])
    def test_hq_database_unreachable(self):
        p=sample();p['hq']['body']['hq_database']['reachable']=False;self.assertFalse(self.check(p)['independent_hq_readonly'])
    def test_recovery_200_cannot_implicitly_promote(self):
        p=sample();p['recovery']['http']=200;self.assertFalse(self.check(p)['original_production_hold_confirmed']);self.assertFalse(self.check(p)['authority_granted'])
    def test_edge_writes_enabled_rejected(self):
        p=sample();p['edge']['body']['writes']=True;self.assertFalse(self.check(p)['legacy_edge_readonly'])
    def test_aether_events_enabled_rejected(self):
        p=sample();p['aether']['body']['event_actions_enabled']=True;self.assertFalse(self.check(p)['aether_events_disabled'])
    def test_octopus_truth_available_cannot_certify_revenue(self):
        p=sample();p['octopus']['body']['durable_truth']['available']=True;self.assertFalse(self.check(p)['octopus_durable_truth_unavailable']);self.assertEqual(self.check(p)['engineer_estimate_percent'],25)
    def test_empty_probes_fail_closed(self):
        a=self.check({});self.assertFalse(a['supervisor_live']);self.assertFalse(a['original_production_hold_confirmed']);self.assertFalse(a['can_dispatch_work'])
    def test_markdown_flags_unverified(self):
        s=markdown(self.check(sample()));self.assertIn('NOT_VERIFIED',s);self.assertIn('~25%',s)
if __name__=='__main__':unittest.main(verbosity=2)