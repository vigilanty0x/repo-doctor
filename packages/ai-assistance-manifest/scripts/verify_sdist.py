"""Safely extract and test one AI Assistance Manifest source distribution."""
from __future__ import annotations
import argparse, os, subprocess, sys, tarfile, tempfile
from pathlib import Path

REQUIRED={"/.github/workflows/ci.yml","/MIGRATION-0.2.md","/release-policy.v1.json","/requirements-build.txt","/docs/RELEASE.md","/scripts/build_release_evidence.py","/scripts/check_release_policy.py","/scripts/verify_counterproof.py","/src/ai_assistance_manifest/schema/manifest.schema.json","/src/ai_assistance_manifest/templates/AI_ASSISTANCE.example.json"}
class SdistError(ValueError): pass

def verify_sdist(archive: Path)->None:
    if not archive.is_file(): raise SdistError("sdist is missing")
    with tempfile.TemporaryDirectory(prefix='aim-sdist-') as tmp:
        destination=Path(tmp).resolve()
        with tarfile.open(archive,'r:gz') as bundle:
            members=bundle.getmembers(); names={m.name for m in members}
            missing=[s for s in REQUIRED if not any(n.endswith(s) for n in names)]
            if missing: raise SdistError(f"incomplete sdist: {missing!r}")
            for member in members:
                target=(destination/member.name).resolve()
                if member.issym() or member.islnk() or not target.is_relative_to(destination): raise SdistError(f"unsafe sdist path: {member.name}")
            bundle.extractall(destination,members=members)
        roots=[p for p in destination.iterdir() if p.is_dir()]
        if len(roots)!=1: raise SdistError("sdist must contain one top-level directory")
        root=roots[0]; env=dict(os.environ); env['PYTHONPATH']=str(root/'src')
        subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=root,env=env,check=True)
        subprocess.run([sys.executable,'scripts/check_release_policy.py'],cwd=root,env=env,check=True)
        subprocess.run([sys.executable,'scripts/verify_counterproof.py'],cwd=root,env=env,check=True)

def main(argv=None)->int:
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);a=p.parse_args(argv)
    try: verify_sdist(a.archive)
    except (OSError,tarfile.TarError,subprocess.CalledProcessError,SdistError) as exc: raise SystemExit(f"sdist verification: {exc}") from exc
    print(f"sdist verified: {a.archive.name}");return 0
if __name__=='__main__': raise SystemExit(main())
