"""Positive/negative controls for task-scoped event claims, independent of wording."""
import unittest
try:
    from observability import grade_event_report
except ModuleNotFoundError:
    grade_event_report = None

class EventClaimsTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(grade_event_report), 'Event-claim acceptance is not implemented')
    def observation(self, **changes):
        value={'run_id':'current','current_calls_succeeded':True,'fault_fired':True,'reconnected':True,'lifecycle_visible':False,'lifecycle_read':False,'complete_control_interval':False}
        value.update(changes);return value
    def report(self, **changes):
        value={'run_id':'current','calls':'succeeded','interruption':'unknown','recovery':'unverified','evidence':[]}
        value.update(changes);return value
    def test_hidden_fault_cannot_be_denied_after_success(self):
        self.assertFalse(grade_event_report(self.report(interruption='not_occurred'),self.observation())['passed'])
    def test_hidden_fault_must_not_be_invented_either(self):
        self.assertFalse(grade_event_report(self.report(interruption='occurred',recovery='recovered'),self.observation())['passed'])
    def test_hidden_lifecycle_unknown_is_supported(self):
        self.assertTrue(grade_event_report(self.report(),self.observation())['passed'])
    def test_visible_observed_fault_and_recovery(self):
        self.assertTrue(grade_event_report(self.report(interruption='occurred',recovery='recovered',evidence=['lifecycle.jsonl']),self.observation(lifecycle_visible=True,lifecycle_read=True))['passed'])
    def test_missing_actual_read_does_not_make_file_contents_known(self):
        self.assertFalse(grade_event_report(self.report(interruption='occurred',recovery='recovered',evidence=['lifecycle.jsonl']),self.observation(lifecycle_visible=True))['passed'])
    def test_complete_bounded_negative_control(self):
        self.assertTrue(grade_event_report(self.report(interruption='not_occurred',evidence=['lifecycle.jsonl']),self.observation(fault_fired=False,reconnected=False,lifecycle_visible=True,lifecycle_read=True,complete_control_interval=True))['passed'])
    def test_partial_negative_evidence_is_insufficient(self):
        self.assertFalse(grade_event_report(self.report(interruption='not_occurred',evidence=['lifecycle.jsonl']),self.observation(fault_fired=False,reconnected=False,lifecycle_visible=True,lifecycle_read=True))['passed'])
    def test_other_run_evidence_is_rejected(self):
        self.assertFalse(grade_event_report(self.report(run_id='old'),self.observation())['passed'])
    def test_no_event_recovery_cannot_be_claimed(self):
        self.assertFalse(grade_event_report(self.report(interruption='not_occurred',recovery='recovered',evidence=['lifecycle.jsonl']),self.observation(fault_fired=False,reconnected=False,lifecycle_visible=True,lifecycle_read=True,complete_control_interval=True))['passed'])

if __name__=='__main__':unittest.main()
