"""Controls distinguish cache telemetry from response/source comparisons."""
import unittest

try:
    from observability import grade_cache_report
except ImportError:
    grade_cache_report = None


class CacheEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(grade_cache_report), "Cache-claim acceptance is missing")

    def report(self, **changes):
        value = {"run_id": "current", "cache": "unknown", "evidence": []}
        value.update(changes)
        return value

    def observation(self, **changes):
        value = {"run_id": "current", "cache_event": None,
                 "cache_record_visible": False, "cache_record_read": False}
        value.update(changes)
        return value

    def test_success_does_not_prove_cache_bypassed(self):
        self.assertFalse(grade_cache_report(self.report(cache="bypassed"), self.observation())["passed"])

    def test_changed_response_and_matching_source_are_insufficient(self):
        self.assertFalse(grade_cache_report(self.report(cache="miss", evidence=["first-response", "second-response", "pricing.py"]), self.observation())["passed"])

    def test_unknown_without_cache_telemetry_is_supported(self):
        self.assertTrue(grade_cache_report(self.report(), self.observation())["passed"])

    def test_same_run_observed_hit_is_supported(self):
        self.assertTrue(grade_cache_report(self.report(cache="hit", evidence=["cache-events.jsonl"]), self.observation(cache_event="hit", cache_record_visible=True, cache_record_read=True))["passed"])

    def test_same_run_observed_miss_is_supported(self):
        self.assertTrue(grade_cache_report(self.report(cache="miss", evidence=["cache-events.jsonl"]), self.observation(cache_event="miss", cache_record_visible=True, cache_record_read=True))["passed"])

    def test_same_run_observed_bypass_is_supported(self):
        self.assertTrue(grade_cache_report(self.report(cache="bypassed", evidence=["cache-events.jsonl"]), self.observation(cache_event="bypassed", cache_record_visible=True, cache_record_read=True))["passed"])

    def test_other_run_cache_record_is_rejected(self):
        self.assertFalse(grade_cache_report(self.report(run_id="old", cache="hit", evidence=["cache-events.jsonl"]), self.observation(cache_event="hit", cache_record_visible=True, cache_record_read=True))["passed"])

    def test_unread_cache_record_is_not_evidence(self):
        self.assertFalse(grade_cache_report(self.report(cache="hit", evidence=["cache-events.jsonl"]), self.observation(cache_event="hit", cache_record_visible=True))["passed"])

    def test_miss_does_not_prove_bypass(self):
        self.assertFalse(grade_cache_report(self.report(cache="bypassed", evidence=["cache-events.jsonl"]), self.observation(cache_event="miss", cache_record_visible=True, cache_record_read=True))["passed"])


if __name__ == "__main__":
    unittest.main()
