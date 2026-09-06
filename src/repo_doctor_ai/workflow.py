"""One repository assessment: scan, remediation, dependency inventory and regression."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .config import Config, ConfigError
from .diffing import diff_reports, load_report
from .planning import build_plan
from .sanitization import safe_output_text
from .sbom import build_sbom
from .scanner import Scanner


def _write(directory: Path, name: str, value: Any) -> str:
    encoded=(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    with (directory/name).open('xb') as stream:
        stream.write(encoded);stream.flush();os.fsync(stream.fileno())
    return hashlib.sha256(encoded).hexdigest()


def run_workflow(root: str | Path, output: str | Path, *, config: Config | None=None,
                 baseline: str | Path | None=None, fail_on: str='high') -> dict[str, Any]:
    """Write a new evidence directory; never execute or modify target code.

    Each bounded phase observes the same path. No immutable source snapshot is
    claimed: operators can pass an isolated checkout when that is required.
    Existing output and outputs inside the scanned repository are refused.
    """
    if fail_on not in {'none','low','medium','high','critical'}:
        raise ConfigError('invalid workflow severity threshold')
    source=Path(root).resolve(strict=True)
    if not source.is_dir(): raise ConfigError('workflow source must be a directory')
    target=Path(output)
    if target.exists() or target.is_symlink(): raise ConfigError('workflow output already exists')
    parent=target.absolute().parent.resolve(strict=True)
    target=parent/target.name
    if target==source or source in target.parents:
        raise ConfigError('workflow output must be outside the scanned repository')
    previous=load_report(baseline) if baseline is not None else None
    policy=config or Config()
    target.mkdir(exist_ok=False)
    result: dict[str,Any]={
        'schema':'repo-doctor-workflow/1','state':'RUNNING','gate_passed':False,
        'fail_on':fail_on,'source_snapshot':'not_created','target_code_executed':False,
        'artifacts':{},'stages':[],
    }
    stage='scan'
    try:
        report=Scanner(policy).scan(source)
        data=report.as_dict()
        result['artifacts']['report.json']=_write(target,'report.json',data)
        result['stages'].append({'stage':stage,'status':report.status})
        stage='remediation'
        plan=build_plan(data)
        result['artifacts']['remediation.json']=_write(target,'remediation.json',plan)
        result['stages'].append({'stage':stage,'status':'completed','work_items':plan['summary']['work_items']})
        stage='dependencies'
        inventory=build_sbom(source,policy)
        result['artifacts']['dependencies.cdx.json']=_write(target,'dependencies.cdx.json',inventory)
        result['stages'].append({'stage':stage,'status':'completed','components':len(inventory.get('components',[]))})
        regression=False
        if previous is not None:
            stage='regression'
            diff=diff_reports(previous,data);regression=diff['regression']
            result['artifacts']['regression.json']=_write(target,'regression.json',diff)
            result['stages'].append({'stage':stage,'status':'completed','regression':regression})
        result['gate_passed']=(report.status=='verified' and not regression
                               and (fail_on=='none' or not report.reaches(fail_on)))
        result['state']='DONE' if report.status=='verified' else 'DEGRADED'
        result['repository_result']=report.result
        result['findings']=len(report.findings)
    except Exception as exc:
        result['state']='FAILED'
        result['stages'].append({'stage':stage,'status':'failed','error_type':type(exc).__name__,
                                 'reason':safe_output_text(str(exc))[:500]})
    _write(target,'result.json',result)
    return result
