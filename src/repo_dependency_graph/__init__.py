import argparse,hashlib,json,re
def graph(data):
 repos=data.get("repositories") if isinstance(data,dict) else None
 if not isinstance(repos,list) or len(repos)>500:return {"ok":False,"errors":["repository_bound"]}
 names=[r.get("name") for r in repos if isinstance(r,dict)]
 if len(names)!=len(repos) or len(names)!=len(set(names)) or any(not isinstance(n,str) or not re.fullmatch(r"[A-Za-z0-9_.-]+",n) for n in names):return {"ok":False,"errors":["invalid_names"]}
 edges=[]
 for r in repos:
  deps=r.get("dependencies",[])
  if not isinstance(deps,list) or any(d not in names for d in deps):return {"ok":False,"errors":["unknown_dependency"]}
  edges.extend((r["name"],d) for d in sorted(set(deps)))
 visiting=set();visited=set();cycles=[];adj={n:[] for n in names}
 for a,b in edges:adj[a].append(b)
 def walk(n,path):
  if n in visiting:cycles.append(path[path.index(n):]+[n]);return
  if n in visited:return
  visiting.add(n)
  for d in adj[n]:walk(d,path+[d])
  visiting.remove(n);visited.add(n)
 for n in sorted(names):walk(n,[n])
 lines=["digraph repositories {"]+[f'  "{a}" -> "{b}";' for a,b in sorted(edges)]+["}"];body={"nodes":sorted(names),"edges":[list(x) for x in sorted(edges)],"cycles":cycles,"dot":"\n".join(lines),"acyclic":not cycles};return {"ok":True,**body,"graph_sha256":hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()}
def probe():
 g=graph({"repositories":[{"name":"a","dependencies":[]}]});b=graph({"repositories":[{"name":"a","dependencies":["missing"]}]});return {"ok":g["ok"] and not b["ok"],"unknown_counter_proof":not b["ok"]}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("command",choices=("graph","probe"));p.add_argument("--input");a=p.parse_args(argv);o=probe() if a.command=="probe" else graph(json.load(open(a.input)));print(json.dumps(o,sort_keys=True));return 0 if o["ok"] else 2
