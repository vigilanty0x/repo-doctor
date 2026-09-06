import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from repo_doctor_ai.cli import main
from repo_doctor_ai.config import Config
from repo_doctor_ai.lock_drift import audit_lock_drift,compare_version_maps
from repo_doctor_ai.registry import RegistryError
from repo_doctor_ai.registry import RulePlugin,RuleRegistry,RegistryDeadlineExceeded

from repo_doctor_ai.rules import SourceFile,build_default_registry
from repo_doctor_ai.scanner import Scanner
from repo_doctor_ai.workflow import run_workflow

def source(path,value):
    text=json.dumps(value,sort_keys=True)
    return SourceFile(path,len(text.encode()),text)

def pair(declared=None,recorded=None):
    declared={'sample-package':'1.0.0'} if declared is None else declared
    recorded={'sample-package':'1.0.0'} if recorded is None else recorded
    return [source('package.json',{'dependencies':declared}),source('package-lock.json',{
        'lockfileVersion':3,'packages':{'node_modules/'+name:{'version':version} for name,version in recorded.items()}})]

class LockDriftTests(unittest.TestCase):
    def test_source_parity_on_positive_negative_and_varied_maps(self):
        path=Path(__file__).parent/'source_oracles/dependency_drift_reporter_core.py'
        spec=importlib.util.spec_from_file_location('original_dependency_drift',path)
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),'7a0ead0beb9a0150e4352d41966847c52736e744d311ed1c1ee11ed678f1ff90')
        cases=[({'a':'1'},{'a':'1'}),({'a':'1'},{'a':'2'}),({'a':'1'},{'b':'1'})]
        rng=random.Random(77)
        for _ in range(100):
            cases.append(({name:str(rng.randint(1,4)) for name in rng.sample(['a','b','c','d'],rng.randint(1,4))},
                          {name:str(rng.randint(1,4)) for name in rng.sample(['a','b','c','d'],rng.randint(1,4))}))
        for declared,recorded in cases:
            expected=old.compare_dependencies({'manifest':declared,'installed':recorded})
            expected['drift']=[{'name':r['name'],'declared':r['declared'],'recorded':r['installed']} for r in expected['drift']]
            with self.subTest(declared=declared,recorded=recorded):self.assertEqual(compare_version_maps(declared,recorded),expected)

    def test_map_refusals_and_explicit_known_empty_extension(self):
        for declared,recorded in [({},{}),({'a':True},{'a':'1'}),({'a':'\n'},{'a':'1'}),({'a':'x'*201},{'a':'1'})]:
            with self.assertRaises(ValueError):compare_version_maps(declared,recorded)
        self.assertEqual(compare_version_maps({'a':'1'}, {},allow_empty=True)['drift_count'],1)
        with self.assertRaises(ValueError):compare_version_maps({'a':'1'},{'a':'1'},allow_empty=1)
        with self.assertRaises(ValueError):compare_version_maps({str(i):'x'*200 for i in range(400)},{'a':'1'})

    def test_registered_real_scan_finds_mismatch_and_missing(self):
        for recorded,code in [({'sample-package':'2.0.0'},'DEPENDENCY_LOCK_DRIFT'),({},'DEPENDENCY_LOCK_ENTRY_MISSING')]:
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                for file in pair(recorded=recorded):(root/file.path).write_text(file.text,encoding='utf-8')
                report=Scanner(Config(enabled_categories=('dependencies',))).scan(root)
                self.assertEqual(report.status,'verified');self.assertTrue(report.reaches('high'))
                finding=next(f for f in report.findings if f.code==code)
                self.assertIn('installed_state=not-observed',finding.evidence)
                self.assertNotIn('2.0.0',finding.evidence)
                self.assertEqual(report.metrics['rules_executed'],2)
        names=[p.name for p in build_default_registry().plugins]
        self.assertEqual(names.count('builtin.dependency-lock-drift'),1)

    def test_matching_direct_versions_do_not_report_transitive_extras(self):
        self.assertEqual(list(audit_lock_drift(tuple(pair(recorded={'sample-package':'1.0.0','transitive':'9.0.0'})))),[])
        self.assertEqual(list(audit_lock_drift(tuple(pair(declared={},recorded={})))),[])

    def test_declared_scopes_scoped_names_and_nested_project(self):
        files=[source('nested/package.json',{'dependencies':{'@scope/item':'1.0.0'},'devDependencies':{'dev-tool':'2.0.0'}}),
               source('nested/package-lock.json',{'lockfileVersion':2,'packages':{'node_modules/@scope/item':{'version':'1.0.0'},'node_modules/dev-tool':{'version':'3.0.0'}}}),
               *pair()]
        findings=list(audit_lock_drift(tuple(files)))
        self.assertEqual(len(findings),1);self.assertEqual(findings[0].path,'nested/package.json')
        self.assertIn('dependency=dev-tool',findings[0].evidence)

    def test_ranges_urls_aliases_workspaces_and_links_are_unmeasured(self):
        fake='gh'+'p_'+'A'*36
        for value in ['^1.0.0','workspace:*','npm:other@1.0.0','v1.0.0','https://user:'+fake+'@example.invalid/file']:
            findings=list(audit_lock_drift(tuple(pair(declared={'sample-package':value}))))
            self.assertEqual([f.code for f in findings],['DEPENDENCY_LOCK_UNMEASURED'])
            self.assertNotIn(value,json.dumps([f.as_dict() for f in findings]));self.assertNotIn(fake,json.dumps([f.as_dict() for f in findings]))
        files=pair();files[1]=source('package-lock.json',{'lockfileVersion':3,'packages':{'node_modules/sample-package':{'link':True,'resolved':'../outside'}}})
        self.assertIn('linked-package',list(audit_lock_drift(tuple(files)))[0].evidence)

    def test_conflicting_scopes_and_shrinkwrap_precedence_are_explicit(self):
        files=pair();files[0]=source('package.json',{'dependencies':{'sample-package':'1.0.0'},'devDependencies':{'sample-package':'2.0.0'}})
        self.assertIn('conflicting-direct-scopes',list(audit_lock_drift(tuple(files)))[0].evidence)
        files=pair()+[source('npm-shrinkwrap.json',{'ignored':'not parsed'})]
        self.assertIn('shrinkwrap-precedence',list(audit_lock_drift(tuple(files)))[0].evidence)
        self.assertIn('package-lock-not-observed',list(audit_lock_drift(tuple(pair()[:1])))[0].evidence)

    def test_optional_overlap_and_overrides_do_not_invent_drift(self):
        for extra,reason in [({'optionalDependencies':{'sample-package':'2.0.0'}},'optional-scope-overlap'),
                             ({'overrides':{'sample-package':'2.0.0'}},'overrides-not-resolved')]:
            files=pair(recorded={'sample-package':'2.0.0'})
            files[0]=source('package.json',{'dependencies':{'sample-package':'1.0.0'},**extra})
            findings=list(audit_lock_drift(tuple(files)))
            self.assertEqual([f.code for f in findings],['DEPENDENCY_LOCK_UNMEASURED'])
            self.assertIn(reason,findings[0].evidence)

    def test_invalid_or_unread_supported_observation_does_not_pass(self):
        files=pair()
        for text in ['{','{"lockfileVersion":3,"lockfileVersion":2}','{"lockfileVersion":3,"packages":[]}',None]:
            bad=SourceFile('package-lock.json',10,text)
            with self.subTest(text=text),self.assertRaises(RegistryError):list(audit_lock_drift((files[0],bad)))
        for version in [1,True,'3']:
            files[1]=source('package-lock.json',{'lockfileVersion':version,'packages':{}})
            self.assertIn('unsupported-lock-version',list(audit_lock_drift(tuple(files)))[0].evidence)

    def test_evidence_is_deterministic_order_bounded_and_hashes_once_per_file(self):
        from repo_doctor_ai import lock_drift
        declared={f'pkg-{i}':'1.0.0' for i in range(30)};recorded={k:'2.0.0' for k in declared}
        files=tuple(pair(declared,recorded));real=lock_drift._hash
        with patch.object(lock_drift,'_hash',wraps=real) as hashed:
            findings=list(audit_lock_drift(files))
        # Each observed text once, plus two short versions per finding.
        self.assertEqual(hashed.call_count,2+2*len(findings))
        self.assertEqual([f.as_dict() for f in findings],[f.as_dict() for f in audit_lock_drift(tuple(reversed(files)))])
        self.assertTrue(all(len(f.evidence.encode())<1000 for f in findings))
        got,executed,truncated=build_default_registry().run(files,('dependencies',),max_findings=2)
        self.assertTrue(truncated);self.assertEqual(len(got),2)

    def test_workflow_cli_and_remediation_consume_real_finding(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);repo=base/'repo';repo.mkdir()
            for file in pair(recorded={'sample-package':'2.0.0'}):(repo/file.path).write_text(file.text,encoding='utf-8')
            sentinel=base/'should-not-exist'
            (repo/'setup.py').write_text('raise RuntimeError("target code must never run")',encoding='utf-8')
            result=run_workflow(repo,base/'result',config=Config(enabled_categories=('dependencies',)))
            self.assertEqual(result['state'],'DONE');self.assertFalse(result['gate_passed']);self.assertFalse(result['target_code_executed'])
            self.assertIn('DEPENDENCY_LOCK_DRIFT',(base/'result/remediation.json').read_text())
            for name,sha in result['artifacts'].items():self.assertEqual(hashlib.sha256((base/'result'/name).read_bytes()).hexdigest(),sha)
            output=io.StringIO();error=io.StringIO()
            with contextlib.redirect_stdout(output),contextlib.redirect_stderr(error):
                exit_code=main(['scan',str(repo),'--format','json','--fail-on','high'])
            self.assertEqual(exit_code,1);self.assertIn('DEPENDENCY_LOCK_DRIFT',output.getvalue());self.assertFalse(sentinel.exists())

    def test_invalid_lock_makes_workflow_failed_even_with_fail_on_none(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);repo=base/'repo';repo.mkdir()
            for file in pair():(repo/file.path).write_text(file.text)
            (repo/'package-lock.json').write_text('{')
            result=run_workflow(repo,base/'result',config=Config(enabled_categories=('dependencies',)),fail_on='none')
            self.assertEqual(result['state'],'FAILED');self.assertFalse(result['gate_passed'])
            self.assertEqual(result['stages'][0]['error_type'],'RegistryError')

    def test_real_lock_link_is_skipped_without_claiming_a_missing_package(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);repo=base/'repo';repo.mkdir()
            (repo/'package.json').write_text(pair()[0].text)
            outside=base/'outside.json';outside.write_text(pair(recorded={'sample-package':'2.0.0'})[1].text)
            try:(repo/'package-lock.json').symlink_to(outside)
            except OSError:self.skipTest('symlink fixture unavailable on this OS')
            report=Scanner(Config(enabled_categories=('dependencies',))).scan(repo)
            codes={f.code for f in report.findings}
            self.assertIn('SCAN_SYMLINK_SKIPPED',codes);self.assertIn('DEPENDENCY_LOCK_UNMEASURED',codes)
            self.assertNotIn('DEPENDENCY_LOCK_DRIFT',codes);self.assertNotIn('DEPENDENCY_LOCK_ENTRY_MISSING',codes)

    def test_registered_rule_honors_cooperative_deadline(self):
        registry=RuleRegistry([RulePlugin('test.lock','dependencies','Synthetic test of real rule',audit_lock_drift)])
        counter=[0]
        def clock():counter[0]+=1;return counter[0]
        with self.assertRaises(RegistryDeadlineExceeded):
            registry.run(tuple(pair()),('dependencies',),max_findings=5,deadline=3,clock=clock)

    def test_documented_cli_example_and_rule_catalog(self):
        project=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            for args,expected in [(['run',str(project/'examples/lock-drift'),'--config',str(project/'examples/dependencies-only.json'),
                                  '--output',str(Path(directory)/'run'),'--fail-on','high'],1),
                                  (['rules','--format','json'],0),(['explain','DEPENDENCY_LOCK_DRIFT'],0)]:
                output=io.StringIO();error=io.StringIO()
                with contextlib.redirect_stdout(output),contextlib.redirect_stderr(error):code=main(args)
                self.assertEqual(code,expected,error.getvalue())
                if args[0]!='run':self.assertIn('DEPENDENCY_LOCK_DRIFT',output.getvalue())

    def test_unmeasured_result_respects_explicit_quality_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);repo=base/'repo';repo.mkdir()
            for file in pair(declared={'sample-package':'^1.0.0'}):(repo/file.path).write_text(file.text)
            policy=Config(enabled_categories=('dependencies',))
            high=run_workflow(repo,base/'high',config=policy,fail_on='high')
            low=run_workflow(repo,base/'low',config=policy,fail_on='low')
            self.assertTrue(high['gate_passed']);self.assertFalse(low['gate_passed'])
            self.assertIn('DEPENDENCY_LOCK_UNMEASURED',(base/'high/report.json').read_text())
