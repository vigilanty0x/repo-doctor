import argparse,hashlib,json
def verify(expected,observed):
 if not isinstance(expected,dict) or not isinstance(observed,dict) or len(expected)>10000:return {"verified":False,"errors":["invalid_manifest"]}
 errors=[]
 for name,want in sorted(expected.items()):
  got=observed.get(name)
  if got is None:errors.append({"path":name,"error":"missing"})
  elif got.get("sha256")!=want.get("sha256") or got.get("size")!=want.get("size"):errors.append({"path":name,"error":"mismatch"})
 for name in sorted(set(observed)-set(expected)):errors.append({"path":name,"error":"unexpected"})
 body={"expected":expected,"observed":observed,"errors":errors};return {"verified":not errors,"errors":errors,"evidence_sha256":hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()}
def probe():
 x={"a":{"sha256":"a"*64,"size":1}};g=verify(x,x);b=verify(x,{});return {"ok":g["verified"] and not b["verified"],"counter_proof":not b["verified"]}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("command",choices=("verify","probe"));p.add_argument("--input");a=p.parse_args(argv);d=json.load(open(a.input)) if a.input else {};o=probe() if a.command=="probe" else verify(d.get("expected"),d.get("observed"));print(json.dumps(o,sort_keys=True));return 0 if o.get("ok",o.get("verified")) else 2
