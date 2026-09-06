"""Exact declared-versus-recorded npm checks over the Scanner's confined inputs.

The comparison follows dependency-drift-reporter (Apache-2.0), with recorded
lock versions explicitly distinguished from an observed installed environment.
This module never opens files, executes package managers or loads target code.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
import re

from .models import Finding
from .registry import RegistryError
from .sanitization import safe_output_text

MAX_MAP_ENTRIES = 2000
MAX_MAP_BYTES = 65536
_PACKAGE = re.compile(r'(?:@[a-z0-9._-]+/)?[a-z0-9._-]+\Z')
_VERSION = re.compile(r'(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z')
HELP = {
    'DEPENDENCY_LOCK_DRIFT': 'An exact direct dependency differs from its recorded npm lock version.',
    'DEPENDENCY_LOCK_ENTRY_MISSING': 'An exact direct dependency has no entry in the observed npm lock.',
    'DEPENDENCY_LOCK_UNMEASURED': 'A dependency lock comparison could not be made within the supported static scope.',
}


def compare_version_maps(declared, recorded, *, allow_empty=False):
    """Compare finite maps exactly; no version resolution or installation claim.

    The source requires nonempty maps. The adapter explicitly allows an observed
    empty lock map so missing entries are reported rather than invented.
    """
    if type(allow_empty) is not bool:
        raise ValueError('allow_empty must be boolean')
    for mapping in (declared, recorded):
        if not isinstance(mapping, dict) or len(mapping)>MAX_MAP_ENTRIES or (not mapping and not allow_empty):
            raise ValueError('version maps must contain a bounded number of entries')
        for key,value in mapping.items():
            for text in (key,value):
                if not isinstance(text,str) or not 0<len(text.strip())<=200 or any(ord(c)<32 or ord(c)==127 for c in text):
                    raise ValueError('names and versions must be bounded single-line strings')
    encoded=json.dumps({'manifest':declared,'installed':recorded},sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    if len(encoded)>MAX_MAP_BYTES:
        raise ValueError('version maps exceed 65536 bytes')
    keys=sorted(set(declared)|set(recorded))
    drift=[{'name':key,'declared':declared.get(key),'recorded':recorded.get(key)}
           for key in keys if declared.get(key)!=recorded.get(key)]
    return {'drift':drift,'checked':keys,'drift_count':len(drift)}


def _unavailable(file,reason):
    # Only a sanitized path and fixed reason are emitted, never parser input.
    raise RegistryError('dependency lock observation unavailable: '+safe_output_text(file.path)+' ('+reason+')')


def _object(file):
    if file.text is None:
        _unavailable(file,'content not read')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('duplicate key')
            result[key]=value
        return result
    def nonfinite(_):raise ValueError('nonfinite value')
    try:
        value=json.loads(file.text,object_pairs_hook=pairs,parse_constant=nonfinite)
    except (ValueError,RecursionError):
        _unavailable(file,'invalid JSON')
    if not isinstance(value,dict):_unavailable(file,'object required')
    return value


def _hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _finding(code,file,*,observed_hashes,name=None,reason=None,declared=None,recorded=None,lock=None):
    parts=['mode=declared-vs-lock-recorded','installed_state=not-observed',
           'manifest_text_sha256='+observed_hashes[file.path]]
    if lock is not None:parts.append('lock_text_sha256='+observed_hashes[lock.path])
    if name is not None:parts.append('dependency='+safe_output_text(name))
    if reason is not None:parts.append('reason='+reason)
    if declared is not None:parts.append('declared_sha256='+_hash(declared))
    if recorded is not None:parts.append('recorded_sha256='+_hash(recorded))
    incomplete=code=='DEPENDENCY_LOCK_UNMEASURED'
    return Finding(code,'dependencies','low' if incomplete else 'high',
                   'inference' if incomplete else 'proof',HELP[code],
                   'Review the direct declaration and regenerate the lock in the trusted build workflow; this audit does not install anything.',
                   file.path,None,'; '.join(parts))


def audit_lock_drift(files):
    """Registered, bounded checks of sibling package.json/package-lock v2/v3.

    Ranges, aliases, links, workspaces and other lock formats are not resolved.
    Malformed supported JSON makes rule execution fail, never a healthy result.
    """
    inventory={file.path:file for file in files
               if PurePosixPath(file.path).name in {'package.json','package-lock.json','npm-shrinkwrap.json'}}
    observed_hashes={path:_hash(file.text or '') for path,file in inventory.items()}
    for path in sorted(inventory):
        if PurePosixPath(path).name!='package.json':continue
        manifest=inventory[path]
        document=_object(manifest)
        declarations={};conflicts=set()
        for section in ('dependencies','devDependencies'):
            mapping=document.get(section,{})
            if not isinstance(mapping,dict):_unavailable(manifest,'dependency map required')
            if len(mapping)>MAX_MAP_ENTRIES:_unavailable(manifest,'dependency map limit')
            for name,version in mapping.items():
                if not isinstance(name,str) or not isinstance(version,str):_unavailable(manifest,'dependency strings required')
                if name in declarations and declarations[name]!=version:conflicts.add(name)
                declarations[name]=version
        if len(declarations)>MAX_MAP_ENTRIES:_unavailable(manifest,'dependency map limit')
        if not declarations:continue
        optional=document.get('optionalDependencies',{})
        if not isinstance(optional,dict):_unavailable(manifest,'optional dependency map required')
        parent=PurePosixPath(path).parent
        lock=inventory.get((parent/'package-lock.json').as_posix())
        if document.get('overrides'):
            yield _finding('DEPENDENCY_LOCK_UNMEASURED',manifest,observed_hashes=observed_hashes,reason='overrides-not-resolved',lock=lock)
            continue
        if (parent/'npm-shrinkwrap.json').as_posix() in inventory:
            yield _finding('DEPENDENCY_LOCK_UNMEASURED',manifest,observed_hashes=observed_hashes,reason='shrinkwrap-precedence',lock=lock)
            continue
        if lock is None:
            yield _finding('DEPENDENCY_LOCK_UNMEASURED',manifest,observed_hashes=observed_hashes,reason='package-lock-not-observed')
            continue
        locked=_object(lock)
        if type(locked.get('lockfileVersion')) is not int or locked['lockfileVersion'] not in (2,3):
            yield _finding('DEPENDENCY_LOCK_UNMEASURED',manifest,observed_hashes=observed_hashes,reason='unsupported-lock-version',lock=lock)
            continue
        packages=locked.get('packages')
        if not isinstance(packages,dict):_unavailable(lock,'packages object required')
        exact={};recorded={}
        for name,version in sorted(declarations.items()):
            if len(name)>200 or not _PACKAGE.fullmatch(name):
                yield _finding('DEPENDENCY_LOCK_UNMEASURED',manifest,observed_hashes=observed_hashes,reason='unsupported-package-name',lock=lock)
                continue
            if name in optional:
                yield _finding('DEPENDENCY_LOCK_UNMEASURED',manifest,observed_hashes=observed_hashes,name=name,reason='optional-scope-overlap',lock=lock)
                continue
            if name in conflicts:
                yield _finding('DEPENDENCY_LOCK_UNMEASURED',manifest,observed_hashes=observed_hashes,name=name,reason='conflicting-direct-scopes',lock=lock)
                continue
            if len(version)>200 or not _VERSION.fullmatch(version):
                yield _finding('DEPENDENCY_LOCK_UNMEASURED',manifest,observed_hashes=observed_hashes,name=name,reason='nonexact-declaration',lock=lock)
                continue
            key='node_modules/'+name
            if key in packages:
                node=packages[key]
                if not isinstance(node,dict):_unavailable(lock,'package entry object required')
                if 'link' in node and type(node['link']) is not bool:_unavailable(lock,'link flag must be boolean')
                if node.get('link'):
                    yield _finding('DEPENDENCY_LOCK_UNMEASURED',manifest,observed_hashes=observed_hashes,name=name,reason='linked-package',lock=lock)
                    continue
                value=node.get('version')
                if not isinstance(value,str) or len(value)>200 or not _VERSION.fullmatch(value):
                    yield _finding('DEPENDENCY_LOCK_UNMEASURED',manifest,observed_hashes=observed_hashes,name=name,reason='recorded-version-unusable',lock=lock)
                    continue
                recorded[name]=value
            exact[name]=version
        try:comparison=compare_version_maps(exact,recorded,allow_empty=True)
        except ValueError:_unavailable(manifest,'comparison byte limit')
        for row in comparison['drift']:
            code='DEPENDENCY_LOCK_ENTRY_MISSING' if row['recorded'] is None else 'DEPENDENCY_LOCK_DRIFT'
            yield _finding(code,manifest,observed_hashes=observed_hashes,name=row['name'],declared=row['declared'],recorded=row['recorded'],lock=lock)
