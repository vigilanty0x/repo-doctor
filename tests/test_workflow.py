import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import contextlib
import io

from repo_doctor_ai.cli import main
from repo_doctor_ai.config import Config, ConfigError
from repo_doctor_ai.workflow import run_workflow


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.repo=self.base/'repo';self.repo.mkdir()
        (self.repo/'README.md').write_text('# Fixture\n',encoding='utf-8')
        (self.repo/'pyproject.toml').write_text('[project]\nname="fixture"\nversion="1.0.0"\ndependencies=["demo==1.2"]\n',encoding='utf-8')
        (self.repo/'danger.py').write_text('raise RuntimeError("must never execute")',encoding='utf-8')

    def test_one_run_produces_linked_physical_evidence_without_execution(self):
        result=run_workflow(self.repo,self.base/'evidence',fail_on='none')
        self.assertEqual(result['state'],'DONE');self.assertTrue(result['gate_passed'])
        self.assertFalse(result['target_code_executed'])
        for name,digest in result['artifacts'].items():
            self.assertEqual(hashlib.sha256((self.base/'evidence'/name).read_bytes()).hexdigest(),digest)
        self.assertEqual(set(result['artifacts']),{'report.json','remediation.json','dependencies.cdx.json'})
        inventory=json.loads((self.base/'evidence/dependencies.cdx.json').read_text(encoding='utf-8'))
        self.assertTrue(any(c['name']=='demo' for c in inventory['components']))

    def test_gate_remains_red_on_observed_high_findings(self):
        result=run_workflow(self.repo,self.base/'evidence',fail_on='low')
        self.assertEqual(result['state'],'DONE');self.assertFalse(result['gate_passed'])
        self.assertGreater(result['findings'],0)

    def test_existing_output_and_self_pollution_are_refused(self):
        output=self.base/'evidence';output.mkdir();(output/'keep').write_text('unchanged')
        with self.assertRaises(ConfigError): run_workflow(self.repo,output)
        self.assertEqual((output/'keep').read_text(),'unchanged')
        with self.assertRaises(ConfigError): run_workflow(self.repo,self.repo/'result')
        self.assertFalse((self.repo/'result').exists())

    def test_bounded_failure_is_recorded_as_failure(self):
        result=run_workflow(self.repo,self.base/'evidence',config=Config(max_files=1),fail_on='none')
        self.assertFalse(result['gate_passed']);self.assertNotEqual(result['state'],'DONE')
        self.assertTrue((self.base/'evidence/result.json').is_file())

    def test_baseline_report_feeds_actual_regression(self):
        run_workflow(self.repo,self.base/'before',fail_on='none')
        result=run_workflow(self.repo,self.base/'after',baseline=self.base/'before/report.json',fail_on='none')
        self.assertTrue(result['gate_passed']);self.assertIn('regression.json',result['artifacts'])
        self.assertFalse(json.loads((self.base/'after/regression.json').read_text())['regression'])

    def test_public_cli_returns_and_writes_the_same_result(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            code=main(['run',str(self.repo),'--output',str(self.base/'cli'),'--fail-on','none'])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(output.getvalue()),json.loads((self.base/'cli/result.json').read_text()))
