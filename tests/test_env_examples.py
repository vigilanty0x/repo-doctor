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

from repo_doctor_ai import env_examples as env
from repo_doctor_ai.cli import main
from repo_doctor_ai.config import Config, DEFAULT_EXCLUDES
from repo_doctor_ai.io_utils import ConfinedReader
from repo_doctor_ai.registry import RegistryError, RegistryDeadlineExceeded, RulePlugin, RuleRegistry
from repo_doctor_ai.rules import SourceFile, build_default_registry

from repo_doctor_ai.workflow import run_workflow


def source(name, text):
    return SourceFile(name, len(text.encode()) if text is not None else 0, text)


def files(text="APP_MODE=demo\nAPI_KEY=\n", keys=("APP_MODE", "API_KEY"), parent=""):
    prefix = parent + "/" if parent else ""
    return (source(prefix + ".env.example", text), source(prefix + ".env.keys.json",
        json.dumps({"schema": "repo-doctor/env-keys-v1", "keys": list(keys)})))


def policy():
    return Config(exclude=DEFAULT_EXCLUDES + (".env",), enabled_categories=("secrets",))


class EnvExampleTests(unittest.TestCase):
    def test_exact_historical_oracle_positive_negative_and_varied(self):
        path = Path(__file__).parent / "source_oracles/env_example_guard_core.py"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         "ae6effa36178ceeafbe622094a5b979d9d389e825f0c5be723c6ea6a25823ee2")
        spec = importlib.util.spec_from_file_location("original_env_example_guard", path)
        original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
        cases = [([], ""), (["API_KEY"], "API_KEY=\n"), (["APP_MODE"], "APP_MODE=demo\n"),
                 (["PASSWORD"], "PASSWORD=synthetic-only\n"), (["A"], "B=1\n")]
        rng = random.Random(112)
        names = ["A", "B", "API_KEY", "DATABASE_URL", "SECRET", "MODE"]
        for _ in range(100):
            keys = rng.sample(names, rng.randrange(7))
            present = rng.sample(names, rng.randrange(7))
            text = "\n".join(key + "=" + rng.choice(["", "changeme", "example", "synthetic-only", "demo"]) for key in present)
            cases.append((keys, text))
        for keys, text in cases:
            with self.subTest(keys=keys, example_sha=hashlib.sha256(text.encode()).hexdigest()):
                self.assertEqual(env.compare_example(keys, text), original.check(keys, text))

    def test_sensitive_policy_independent_of_declared_names(self):
        shapes = ["AKIA" + "A"*16, "github" + "_pat_" + "A"*24, "xox" + "b-" + "A"*24,
                  "sk" + "_live_" + "A"*24, "eyJ"+"a"*8+"."+"b"*10+"."+"c"*10]
        for value in ["synthetic-only", *shapes]:
            key = "PASSWORD" if value == "synthetic-only" else "APP_MODE"
            records = list(env.audit_env_examples(files(key + "=" + value + "\n", keys=())))
            self.assertIn("ENV_EXAMPLE_SECRET_VALUE", [f.code for f in records])
            self.assertNotIn(value, json.dumps([f.as_dict() for f in records]))

    def test_all_original_placeholders_case_and_simple_parse_semantics(self):
        for value in env.PLACEHOLDERS:
            self.assertEqual(list(env.audit_env_examples(files("API_KEY=" + value.upper() + "\n", ("API_KEY",)))), [])
        self.assertEqual(env.parse_example("# heading\r\n\r\nAPI_KEY=\r\n")[1], {"API_KEY": 3})
        quoted = list(env.audit_env_examples(files('API_KEY=""\n', ("API_KEY",))))
        self.assertEqual(quoted[0].code, "ENV_EXAMPLE_SECRET_VALUE")

    def test_missing_extra_and_location_are_deterministic(self):
        records = list(env.audit_env_examples(files("B=demo\nAPI_KEY=\n", ("API_KEY", "A"))))
        self.assertEqual([f.code for f in records], ["ENV_EXAMPLE_KEY_MISSING", "ENV_EXAMPLE_KEY_EXTRA"])
        self.assertIsNone(records[0].line); self.assertEqual(records[1].line, 1)
        self.assertIn("key=A", records[0].evidence); self.assertIn("key=B", records[1].evidence)
        self.assertIn("loaded_environment=not-observed", records[0].evidence)
        self.assertTrue(all(f.severity == "high" and f.classification == "proof" for f in records))

    def test_no_manifest_keeps_hygiene_and_explicit_unknown(self):
        records = list(env.audit_env_examples((source(".env.example", "PASSWORD=synthetic-only\n"),)))
        self.assertEqual([f.code for f in records], ["ENV_EXAMPLE_SECRET_VALUE", "ENV_EXAMPLE_KEYS_UNMEASURED"])
        self.assertEqual(records[-1].classification, "inference")
        self.assertEqual(records[-1].severity, "low")
        self.assertIn("key_parity=not-measured", records[-1].evidence)

    def test_scopes_do_not_merge_sibling_projects_and_order_stable(self):
        records = (*files("PASSWORD=synthetic-only\n", ("PASSWORD",), "b"), *files(parent="a"))
        result = list(env.audit_env_examples(records))
        self.assertEqual([f.path for f in result], ["b/.env.example"])
        self.assertEqual(result, list(env.audit_env_examples(tuple(reversed(records)))))

    def test_only_two_exact_names_and_no_rule_io(self):
        allowed = files()
        ignored = (source(".env", "PASSWORD=real-read-forbidden"), source(".env.local", "PASSWORD=ignored"),
                   source("env.example", "PASSWORD=ignored"), source(".ENV.EXAMPLE", "PASSWORD=ignored"))
        with patch("builtins.open", side_effect=AssertionError("new rule must not open files")), \
             patch("os.getenv", side_effect=AssertionError("new rule must not read environment")):
            self.assertEqual(list(env.audit_env_examples((*allowed, *ignored))), [])

    def test_invalid_example_never_echoes_input(self):
        for text in (None, "PASSWORD=synthetic-only\nPASSWORD=synthetic-only\n", "lower=value\n",
                     "export PASSWORD=synthetic-only\n", "PASSWORD\n", "BAD KEY=value", "A=\ufffd"):
            with self.subTest(text_hash=hashlib.sha256((text or "").encode()).hexdigest()):
                with self.assertRaises(RegistryError) as captured:
                    list(env.audit_env_examples((source(".env.example", text),)))
                self.assertNotIn("synthetic-only", str(captured.exception))

    def test_manifest_invalid_shapes_fields_numbers_and_duplicate_keys(self):
        bad = [None, "{", "[]", '{"schema":"repo-doctor/env-keys-v1","schema":"x","keys":[]}',
               '{"schema":"repo-doctor/env-keys-v1","keys":["A","A"]}',
               '{"schema":"repo-doctor/env-keys-v1","keys":[true]}',
               '{"schema":"repo-doctor/env-keys-v1","keys":[NaN]}',
               '{"schema":"repo-doctor/env-keys-v1","keys":[],"secret_keys":[]}',
               '{"schema":"repo-doctor/env-keys-v2","keys":[]}',
               '{"schema":"repo-doctor/env-keys-v1","keys":{}}']
        for text in bad:
            with self.subTest(text_hash=hashlib.sha256((text or "").encode()).hexdigest()), self.assertRaises(RegistryError):
                list(env.audit_env_examples((source(".env.example", "API_KEY=\n"),source(".env.keys.json", text))))

    def test_inconclusive_empty_or_example_not_observed_is_error(self):
        for records in (files("",()), files("# only comment\n",()), (source(".env.example", ""),), files()[1:]):
            with self.assertRaises(RegistryError): list(env.audit_env_examples(records))

    def test_each_rule_budget_refuses(self):
        for field, limit, records in [("MAX_KEYS",1,files()), ("MAX_EXAMPLE_BYTES",2,files()),
             ("MAX_MANIFEST_BYTES",3,files()), ("MAX_TOTAL_BYTES",5,files()),
             ("MAX_SCOPES",1,(*files(parent="a"),*files(parent="b")))]:
            with self.subTest(bound=field),patch.object(env,field,limit),self.assertRaises(RegistryError):
                list(env.audit_env_examples(records))

    def test_deadline_inside_large_example_and_finding_limit(self):
        registry = RuleRegistry([RulePlugin("test.env", "secrets", "Synthetic env rule", env.audit_env_examples)])
        counter = [0]
        def clock():counter[0]+=1;return counter[0]
        large = (source(".env.example", "\n".join("K"+str(i)+"=v" for i in range(100))),)
        with self.assertRaises(RegistryDeadlineExceeded):
            registry.run(large,("secrets",),max_findings=10,deadline=30,clock=clock)
        rows = files("PASSWORD=synthetic-only\nAPI_KEY=synthetic-only\n", ("PASSWORD","API_KEY"))
        findings, executed, truncated = registry.run(rows,("secrets",),max_findings=1)
        self.assertEqual(len(findings),1);self.assertTrue(truncated);self.assertEqual(executed,("test.env",))

    def test_workflow_traverses_public_names_and_excludes_real_env(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);repo=base/"repo";repo.mkdir()
            for file in files("PASSWORD=synthetic-only\n", ("PASSWORD",)):
                (repo/file.path).write_text(file.text,encoding="utf-8")
            (repo/".env").write_text("synthetic forbidden-read sentinel",encoding="utf-8")
            (repo/"setup.py").write_text('raise RuntimeError("do not execute target")',encoding="utf-8")
            observed=[];native=ConfinedReader.read_bounded_bytes
            def record(reader, relative, *args, **kwargs):
                self.assertNotEqual(relative,".env")
                observed.append(relative)
                return native(reader,relative,*args,**kwargs)
            before={f.path:hashlib.sha256((repo/f.path).read_bytes()).hexdigest() for f in files()}
            with patch.object(ConfinedReader,"read_bounded_bytes",record):
                result=run_workflow(repo,base/"out",config=policy())
            self.assertTrue({".env.example",".env.keys.json"}<=set(observed))
            self.assertNotIn(".env",observed)
            self.assertEqual(result["state"],"DONE");self.assertFalse(result["gate_passed"])
            self.assertFalse(result["target_code_executed"])
            report=json.loads((base/"out/report.json").read_text())
            self.assertTrue(any(f["code"]=="ENV_EXAMPLE_SECRET_VALUE" for f in report["findings"]))
            self.assertIn("ENV_EXAMPLE_SECRET_VALUE",(base/"out/remediation.json").read_text())
            for name,digest in result["artifacts"].items():
                raw=(base/"out"/name).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)
                self.assertNotIn(b"synthetic-only",raw)
            self.assertEqual(before,{f.path:hashlib.sha256((repo/f.path).read_bytes()).hexdigest() for f in files()})

    def test_incomplete_is_failed_even_with_fail_on_none(self):
        for content in (b"A=1\nA=2", b"A=\0", b"A=\xff", b"A="+b"x"*1025):
            with self.subTest(content_bytes=len(content)),tempfile.TemporaryDirectory() as directory:
                base=Path(directory);repo=base/"repo";repo.mkdir()
                (repo/".env.example").write_bytes(content)
                config=Config(enabled_categories=("secrets",),max_file_bytes=1024)
                result=run_workflow(repo,base/"out",config=config,fail_on="none")
                self.assertEqual(result["state"],"FAILED");self.assertFalse(result["gate_passed"])
                self.assertEqual(result["stages"][0]["error_type"],"RegistryError")

    def test_known_matching_and_optional_unknown_thresholds(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);repo=base/"repo";repo.mkdir()
            (repo/".env.example").write_text("APP_MODE=demo\n")
            high=run_workflow(repo,base/"high",config=policy(),fail_on="high")
            low=run_workflow(repo,base/"low",config=policy(),fail_on="low")
            self.assertTrue(high["gate_passed"]);self.assertFalse(low["gate_passed"])
            (repo/".env.keys.json").write_text(files("APP_MODE=demo\n",("APP_MODE",))[1].text)
            matched=run_workflow(repo,base/"matched",config=policy(),fail_on="low")
            self.assertTrue(matched["gate_passed"]);self.assertEqual(matched["findings"],0)

    def test_registered_once_and_public_cli_diagnostics(self):
        plugins=[p.name for p in build_default_registry().plugins]
        self.assertEqual(plugins.count("builtin.env-example"),1)
        for args in (["rules","--format","json"], ["explain","ENV_EXAMPLE_SECRET_VALUE"]):
            out,err=io.StringIO(),io.StringIO()
            with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):code=main(args)
            self.assertEqual(code,0,err.getvalue());self.assertIn("ENV_EXAMPLE_SECRET_VALUE",out.getvalue())

    def test_documented_positive_cli_example(self):
        project=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            out,err=io.StringIO(),io.StringIO()
            with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
                code=main(["run",str(project/"examples/env-example"),"--config",str(project/"examples/env-secrets-only.json"),
                           "--output",str(Path(directory)/"out"),"--fail-on","high"])
            self.assertEqual(code,0,err.getvalue())
            receipt=json.loads((Path(directory)/"out/result.json").read_text())
            self.assertTrue(receipt["gate_passed"]);self.assertEqual(receipt["findings"],0)

    def test_real_link_not_followed_then_manifest_prevents_false_absence(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);repo=base/"repo";repo.mkdir()
            outside=base/"synthetic-public-example";outside.write_text("PASSWORD=synthetic-only\n")
            (repo/".env.keys.json").write_text(files()[1].text)
            try:(repo/".env.example").symlink_to(outside)
            except OSError:self.skipTest("symlink fixture unavailable on this OS")
            result=run_workflow(repo,base/"out",config=policy(),fail_on="none")
            self.assertEqual(result["state"],"FAILED");self.assertFalse(result["gate_passed"])
            self.assertIn("not observed",result["stages"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
