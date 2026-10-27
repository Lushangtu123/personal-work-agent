"""Bounded evaluator for controlled event-report scenarios; not a prose/host hook.

Observation values come from the task controller and actual native trace reads,
not from the candidate's report. They are unsigned local evidence, not a trust
boundary against a hostile controller. This does not grade arbitrary language.
"""

def grade_event_report(report, observation):
    checks = {}
    fields = {'run_id', 'calls', 'interruption', 'recovery', 'evidence'}
    if not isinstance(report, dict) or set(report) != fields or not isinstance(observation, dict):
        return {'passed': False, 'checks': {'valid_schema': False}}
    checks['valid_schema'] = (report['calls'] in ('succeeded', 'failed', 'unknown')
        and report['interruption'] in ('occurred', 'not_occurred', 'unknown')
        and report['recovery'] in ('recovered', 'unverified')
        and isinstance(report['evidence'], list)
        and all(isinstance(x, str) and x for x in report['evidence']))
    checks['same_run'] = report['run_id'] == observation.get('run_id')
    checks['current_calls'] = report['calls'] == ('succeeded' if observation.get('current_calls_succeeded') is True else 'failed')
    visible = observation.get('lifecycle_visible') is True and observation.get('lifecycle_read') is True
    cited = 'lifecycle.jsonl' in report['evidence']
    state = report['interruption']
    if state == 'occurred':
        supported = visible and cited and observation.get('fault_fired') is True
    elif state == 'not_occurred':
        supported = visible and cited and observation.get('fault_fired') is False and observation.get('complete_control_interval') is True
    else:
        supported = not (visible and observation.get('fault_fired') is True)
    checks['interruption_supported_by_visible_evidence'] = supported
    checks['recovery_supported'] = (report['recovery'] == 'unverified' or
        (visible and cited and state == 'occurred' and observation.get('reconnected') is True))
    return {'passed': all(checks.values()), 'checks': checks,
        'scope': 'Structured controlled-task decision plus observed lifecycle/read coverage; free-text final requires independent review.'}


def grade_cache_report(report, observation):
    """Grade a scoped cache decision against observed same-run cache telemetry.

    Successful/different responses and source matches are intentionally not
    cache telemetry. The caller must retain the underlying event and its scope.
    This does not classify arbitrary prose or certify the telemetry provider.
    """
    states = {'hit', 'miss', 'bypassed', 'unknown'}
    if not isinstance(report, dict) or set(report) != {'run_id', 'cache', 'evidence'} or not isinstance(observation, dict):
        return {'passed': False, 'checks': {'valid_schema': False}}
    valid = (isinstance(report['cache'], str) and report['cache'] in states
             and isinstance(report['evidence'], list)
             and all(isinstance(x, str) and x for x in report['evidence']))
    observed = (observation.get('cache_record_visible') is True
                and observation.get('cache_record_read') is True
                and observation.get('cache_event') in states - {'unknown'})
    supported = (report['cache'] == 'unknown' and not observed) or (
        observed and report['cache'] == observation['cache_event']
        and 'cache-events.jsonl' in report['evidence'])
    checks = {'valid_schema': valid, 'same_run': report['run_id'] == observation.get('run_id'),
              'cache_claim_supported': supported}
    return {'passed': all(checks.values()), 'checks': checks,
            'scope': 'Structured cache decision for the supplied same-run telemetry scope, not arbitrary prose or system-wide cache absence.'}
