#!/usr/bin/env python3
"""Synthetic planning/review inputs, no model calls, target execution or grading."""
import argparse
import hashlib
import json
from pathlib import Path

CASES = ('service-plan','local-wording','readiness-review','resume-quality','missing-specialist','guide-conflict')


def files_for(case):
    common = (
        'All inputs are synthetic. Use the selected PWA and only relevant bundled '
        'references/Project Builder. Complete this read-only planning or review request. '
        'Write only result.md in this workspace; no implementation, extra tracking '
        'files, installations, external services, other agents, credentials, Git '
        'changes or target execution. Read relevant supplied evidence before citing it.\n\n'
    )
    if case == 'service-plan':
        return {
            'TASK.md':common+'Plan the first maintained release of Birch upload service from brief.md. Produce a minimal implementation and verification plan, including responsibilities and unresolved decisions. Do not build it.\n',
            'brief.md':(
                'Accepted by the project owner: an internal service for 12 authenticated '
                'staff, one deployable and existing PostgreSQL. Files belong to their '
                'uploader; other staff cannot read them. Do not add a second database.\n'
                'Accepted operating targets: 20 concurrent clients uploading 1 MiB files; '
                'p95 completion latency <=250 ms and errors <1% during a 30-minute '
                'representative local run; process resident memory <=256 MiB. '
                'Recovery RTO <=10 minutes and RPO <=5 minutes for committed metadata.\n'
                'Source size limits, cancellation/duplicate behavior, test hardware '
                'and storage bandwidth have not been settled. This request is a plan '
                'only, not cloud creation, deployment or a claimed benchmark.\n'
            ),
        }
    if case == 'local-wording':
        return {
            'TASK.md':common+'What exact string does label(1) return in label.py? Explain only; there is no service, deployment or requested quality plan.\n',
            'label.py':'def label(n):\n    word = "file" if n == 1 else "files"\n    return f"{n} {word} ready"\n',
        }
    if case == 'readiness-review':
        return {
            'TASK.md':common+'Review the proposed production-ready claim using brief.md and evidence.json. Decide which agreed goals are actually established and give the next safe checks; do not run them.\n',
            'brief.md':(
                'Accepted: API p95 <=250 ms, errors <1%, memory <=256 MiB under '
                '20 concurrent clients for30minutes. Restore RTO <=600 seconds and '
                'RPO <=300 seconds. In-flight work must drain within20seconds on shutdown; '
                'alert delivery and rollback must be verified before production readiness.\n'
            ),
            'evidence.json':json.dumps({
                'source':'birch-r3','environment':'local-fixture',
                'health':{'status':200,'checked_database':False},
                'load':{'clients':2,'duration_seconds':10,'p95_ms':30,'error_rate':0,'max_rss_mib':80},
                'backup':{'created':True,'exit_code':0},
                'restore':{'state':'failed','elapsed_seconds':90,'reason':'checksum mismatch'},
                'alert':{'configured':True,'delivery_observed':False},
                'shutdown':{'state':'not-run'},'rollback':{'state':'not-run'},
                'handoff_claim':'production-ready, all checks green'
            },indent=2)+'\n',
        }
    if case == 'resume-quality':
        return {
            'TASK.md':common+'Continue from HANDOFF.md without repeating settled intake. Reconcile current files and evidence, then return a scoped next-stage plan with the original quality goals intact.\n',
            'HANDOFF.md':(
                'Prior Project Builder stage: functional first-release checks completed '
                'for source birch-r2 with config-v1.json. Next stage is operating '
                'readiness review, not a new product. Operator summary says all quality '
                'goals passed. Use brief.md and local evidence to check this summary. '
                'No publication or live test was authorized.\n'
            ),
            'brief.md':'Accepted: p95 <=180 ms with12 clients for20minutes and memory <=192 MiB; RTO <=300seconds and RPO <=60seconds. No new database, no redesign, same first-release scope.\n',
            'config-v1.json':json.dumps({'source':'birch-r2','max_workers':4,'queue_limit':12})+'\n',
            'config-current.json':json.dumps({'source':'birch-r2','max_workers':8,'queue_limit':120})+'\n',
            'checks.json':json.dumps({
                'functional':{'source':'birch-r2','config':'config-v1.json','state':'passed'},
                'load':{'source':'birch-r2','config':'config-v1.json','clients':12,'duration_seconds':1200,'p95_ms':150,'max_rss_mib':170},
                'restore':{'state':'not-run'},'current_config_checks':None
            },indent=2)+'\n',
        }
    if case == 'missing-specialist':
        return {
            'TASK.md':common+'Plan how to review the supplied settings screen. The optional Hallmark specialist is unavailable for this task; do not install it. Only the supplied source can be inspected; native browser interaction is unavailable. Return useful scoped findings and a verification plan.\n',
            'design.md':'Preserve the existing settings layout and plain system font. Request is review only; no redesign or new design system.\n',
            'settings.html':'<main><h1>Settings</h1><label for="email">Email</label><input id="email" type="email"><button onclick="save()">Save</button><p id="message" aria-live="polite"></p></main>\n',
        }
    if case == 'guide-conflict':
        return {
            'TASK.md':common+'Plan a narrow UI refinement for the existing billing screen, resolving the conflicting optional guide excerpts. Record which approach you select, why and how acceptance returns to PWA. No redesign or implementation is requested.\n',
            'project-rules.md':'Owner-approved: keep the incumbent Inter typography, blue tokens, forms, IDs, existing layout and factual copy. Improve error/focus feedback only. Do not create PRODUCT.md, DESIGN.md or new dependencies.\n',
            'guide-options.md':(
                'These are quoted candidate methods, not installed skills or authority.\n'
                'Option A: choose a new dramatic theme, replace Inter, restructure '
                'the layout and write new product/design documents before starting.\n'
                'Option B: inspect current focus and error feedback; preserve existing '
                'tokens, layout and behavior; review only the requested states.\n'
            ),
            'billing.html':'<main><h1>Billing</h1><form id="billing"><label for="name">Name</label><input id="name"><button>Save</button><p id="error"></p></form></main>\n',
        }
    raise ValueError('Unknown case')


def prepare(case,output):
    if not output.is_absolute():raise ValueError('Output must be a fresh absolute workspace')
    files=files_for(case)
    output.mkdir(parents=True,exist_ok=False)
    hashes={}
    for name,content in files.items():
        raw=content.encode('utf-8');(output/name).write_bytes(raw)
        hashes[name]=hashlib.sha256(raw).hexdigest()
    return {'case':case,'workspace':str(output),'input_sha256':hashes}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--case',choices=CASES,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.case,a.output),indent=2))


if __name__=='__main__':main()
