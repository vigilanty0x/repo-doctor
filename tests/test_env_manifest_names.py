import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from repo_doctor_ai.env_examples import audit_env_examples
from repo_doctor_ai.registry import RegistryError
from repo_doctor_ai.rules import SourceFile
from repo_doctor_ai.config import Config,DEFAULT_EXCLUDES
from repo_doctor_ai.workflow import run_workflow

def manifest(keys):return json.dumps({'schema':'repo-doctor/env-keys-v1','keys':keys})
def src(name,text):return SourceFile(name,len(text.encode()),text)
def example():return src('.env.example','APP_MODE=demo\nAPI_KEY=\n')

class PublicManifestNameTests(unittest.TestCase):
    def test_new_public_name_has_measured_key_parity(self):
        records=[example(),src('env-keys.json',manifest(['APP_MODE','API_KEY']))]
        self.assertEqual(list(audit_env_examples(records)),[])

    def test_new_public_name_detects_missing_extra_keys(self):
        records=[example(),src('env-keys.json',manifest(['APP_MODE','OTHER']))]
        self.assertEqual([f.code for f in audit_env_examples(records)],['ENV_EXAMPLE_KEY_MISSING','ENV_EXAMPLE_KEY_EXTRA'])

    def test_legacy_alias_still_has_measured_key_parity(self):
        self.assertEqual(list(audit_env_examples([example(),src('.env.keys.json',manifest(['APP_MODE','API_KEY']))])),[])

    def test_equal_aliases_accept_different_json_order_but_do_not_merge(self):
        records=[example(),src('env-keys.json',manifest(['APP_MODE','API_KEY'])),src('.env.keys.json',manifest(['API_KEY','APP_MODE']))]
        self.assertEqual(list(audit_env_examples(records)),[])
        self.assertEqual(list(audit_env_examples(reversed(records))),[])

    def test_conflicting_aliases_refused_in_both_orders(self):
        records=[example(),src('env-keys.json',manifest(['APP_MODE','API_KEY'])),src('.env.keys.json',manifest(['OTHER']))]
        for ordered in (records,list(reversed(records))):
            with self.subTest(reverse=ordered is not records),self.assertRaises(RegistryError):list(audit_env_examples(ordered))

    def test_invalid_alias_is_not_hidden_by_good_canonical(self):
        for bad in ('{','{"schema":"repo-doctor/env-keys-v1","keys":["A","A"]}'):
            with self.subTest(bad=bad),self.assertRaises(RegistryError):
                list(audit_env_examples([example(),src('env-keys.json',manifest(['APP_MODE','API_KEY'])),src('.env.keys.json',bad)]))

    def test_no_extension_to_other_configuration_names(self):
        ignored=[src(name,'synthetic-unreadable') for name in ('.env.private','env-keys.local.json','ENV-KEYS.JSON','.env','env.keys.json')]
        result=list(audit_env_examples([example(),*ignored]))
        self.assertEqual([f.code for f in result],['ENV_EXAMPLE_KEYS_UNMEASURED'])

    def test_two_aliases_share_total_budget(self):
        from unittest.mock import patch
        import repo_doctor_ai.env_examples as env
        records=[example(),src('env-keys.json',manifest(['APP_MODE','API_KEY'])),src('.env.keys.json',manifest(['APP_MODE','API_KEY']))]
        limit=sum(len(f.text.encode()) for f in records)-1
        with patch.object(env,'MAX_TOTAL_BYTES',limit),self.assertRaises(RegistryError):list(env.audit_env_examples(records))

    def test_canonical_manifest_without_example_is_incomplete(self):
        with self.assertRaises(RegistryError):list(audit_env_examples([src('env-keys.json',manifest(['A']))]))

    def test_scanner_workflow_measures_public_name_only(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);repo=base/'repo';repo.mkdir()
            (repo/'.env.example').write_text('APP_MODE=demo\nAPI_KEY=\n')
            (repo/'env-keys.json').write_text(manifest(['APP_MODE','API_KEY']))
            # Private-name synthetic sentinel is created but must not be read.
            (repo/'.env').write_text('unreadable-synthetic-sentinel')
            result=run_workflow(repo,base/'result',config=Config(exclude=DEFAULT_EXCLUDES+('.env',),enabled_categories=('secrets',)),fail_on='low')
            self.assertEqual(result['state'],'DONE');self.assertTrue(result['gate_passed'])
            self.assertEqual(result['findings'],0);self.assertFalse(result['target_code_executed'])

if __name__=='__main__':unittest.main()
