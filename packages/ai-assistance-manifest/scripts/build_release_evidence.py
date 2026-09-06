"""Generate bounded release evidence for an AI Assistance Manifest candidate."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import tomllib

MAX_ARTIFACT_BYTES = 128 * 1024 * 1024

class ReleaseEvidenceError(ValueError):
    pass

def _digest(path: Path) -> tuple[int,str]:
    size = path.stat().st_size
    if size > MAX_ARTIFACT_BYTES: raise ReleaseEvidenceError(f"artifact too large: {path.name}")
    h=sha256()
    with path.open('rb') as f:
        while chunk:=f.read(1024*1024): h.update(chunk)
    return size,h.hexdigest()

def build_release_evidence(root: Path, dist: Path, output: Path) -> dict:
    root,dist=root.resolve(),dist.resolve(); output.mkdir(parents=True,exist_ok=True)
    try: project=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))['project']
    except (OSError,UnicodeError,tomllib.TOMLDecodeError,KeyError,TypeError) as exc: raise ReleaseEvidenceError('cannot read project metadata') from exc
    if project.get('name')!='ai-assistance-manifest' or project.get('version')!='0.2.0': raise ReleaseEvidenceError('unexpected distribution identity/version')
    wheels=sorted(dist.glob('*.whl')); sdists=sorted(dist.glob('*.tar.gz'))
    if len(wheels)!=1 or len(sdists)!=1: raise ReleaseEvidenceError(f"expected exactly one wheel and one sdist; found wheels={len(wheels)} sdists={len(sdists)}")
    rows=[]
    for path in (wheels[0],sdists[0]):
        size,digest=_digest(path); rows.append({'name':path.name,'size':size,'sha256':digest})
    rows.sort(key=lambda x:x['name'])
    (output/'SHA256SUMS.txt').write_text(''.join(f"{r['sha256']}  {r['name']}\n" for r in rows),encoding='utf-8')
    bom={'bomFormat':'CycloneDX','specVersion':'1.6','version':1,'metadata':{'component':{'type':'application','name':'AI Assistance Manifest','version':'0.2.0','purl':'pkg:pypi/ai-assistance-manifest@0.2.0'}},'components':[],'properties':[{'name':f"ai-assistance-manifest:artifact:{r['name']}:sha256",'value':r['sha256']} for r in rows]}
    (output/'ai-assistance-manifest.cdx.json').write_text(json.dumps(bom,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    receipt={'schema_version':'1.0','product':'AI Assistance Manifest','repository':'vigilanty0x/ai-assistance-manifest','distribution':'ai-assistance-manifest','version':'0.2.0','manifest_format_version':'1.0','state':'PREPARED','source_sha':os.environ.get('GITHUB_SHA') or 'not-recorded','source_ref':os.environ.get('GITHUB_REF') or 'not-recorded','generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'python':platform.python_version(),'platform':platform.platform(),'artifacts':rows,'checksums':'SHA256SUMS.txt','sbom':'ai-assistance-manifest.cdx.json','tests_verified':os.environ.get('AIM_TESTS_VERIFIED')=='1','counterproof_verified':os.environ.get('AIM_COUNTERPROOF_VERIFIED')=='1','signed':False,'attested':False,'tagged':False,'published':False,'released':False}
    (output/'RELEASE_EVIDENCE.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n',encoding='utf-8'); return receipt

def main(argv=None)->int:
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--dist',type=Path,default=Path('dist'));p.add_argument('--output',type=Path,default=Path('release-evidence'));a=p.parse_args(argv)
    try:r=build_release_evidence(a.root,a.dist,a.output)
    except (OSError,ReleaseEvidenceError) as exc: raise SystemExit(f"release evidence: {exc}") from exc
    print(f"release evidence prepared: version={r['version']} artifacts={len(r['artifacts'])} state={r['state']}");return 0

if __name__=='__main__': raise SystemExit(main())
