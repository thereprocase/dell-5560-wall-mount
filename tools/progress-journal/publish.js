/* Async function body. Runtime arguments: tools, text, config.
 * No destination, workspace or account identity is embedded in this source. Reads the prepared manifest,
 * publishes through the connected GitHub app, and returns the journal URL.
 * No credentials in files; no force pushes. A concurrent branch edit aborts.
 */
if (!config || typeof config.root !== 'string' ||
    !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(config.repository || '') ||
    typeof config.branch !== 'string' || !config.branch) {
  throw new Error('Supply config.root, config.repository and config.branch at runtime');
}
const root = config.root;
const repo = config.repository;
const branch = config.branch;
const manifest = config.manifest || '.journal/publish.json';
const quote=s=>"'"+String(s).replace(/'/g,"'\\''")+"'";
const api = 'https://api.github.com/repos/' + repo;
function payload(r) {
  if (r.isError) throw new Error(JSON.stringify(r));
  let p = r.structuredContent;
  if (!p) throw new Error('Missing structured result');
  return p.result || p;
}
async function readJson(cmd) {
  const r = await tools.exec_command({cmd, workdir:root, max_output_tokens:250000});
  if (r.exit_code !== 0) throw new Error(r.output);
  return JSON.parse(r.output);
}
const files = await readJson(`python3 - ${quote(manifest)} <<'PY'
import json,sys
from pathlib import Path
r=Path.cwd().resolve();mp=(r/sys.argv[1]).resolve();mp.relative_to(r)
m=json.loads(mp.read_text())
if m.get('schema_version') != 1:raise ValueError('Unsupported manifest schema')
jp=(r/m['journal']).resolve();jp.relative_to(r)
out=[]
for name in dict.fromkeys(m['paths']):
 p=(r/name).resolve();p.relative_to(r)
 if not p.is_file():raise FileNotFoundError(p)
 name=p.relative_to(r).as_posix()
 if p.suffix in {'.md','.py','.js','.json','.csv','.txt','.svg'}:
  out.append({'path':name,'content':p.read_text()})
 else:out.append({'path':name,'size':p.stat().st_size})
print(json.dumps({'message':m['message'],'journal':jp.relative_to(r).as_posix(),'branch':m.get('branch'),'files':out}))
PY`);
if(files.branch && files.branch!==branch) throw new Error('Manifest branch does not match destination');
const ref = JSON.parse(payload(await tools.mcp__codex_apps__github_fetch({url:api+'/git/ref/heads/'+encodeURIComponent(branch)})).content);
const parent = ref.object.sha;
const commit = JSON.parse(payload(await tools.mcp__codex_apps__github_fetch({url:api+'/git/commits/'+parent})).content);
const entries=[];
for (const f of files.files) {
  if('content' in f) {entries.push({path:f.path,mode:'100644',type:'blob',content:f.content});continue;}
  const quote=s=>"'"+String(s).replace(/'/g,"'\\''")+"'";
  let encoded='';
  const block=96000;
  const count=Math.ceil(f.size/block);
  for(let start=0;start<count;start+=8) {
    const batch=await Promise.allSettled(Array.from({length:Math.min(8,count-start)},async (_,j)=> {
      const i=start+j;
      const binary=await tools.exec_command({cmd:'dd if='+quote(f.path)+' bs='+block+' skip='+i+' count=1 status=none | base64 -w0',workdir:root,max_output_tokens:150000});
      const data=binary.output.trim();
      const expected=4*Math.ceil(Math.min(block,f.size-i*block)/3);
      if(binary.exit_code!==0 || data.length!==expected || !/^[A-Za-z0-9+/]*={0,2}$/.test(data)) throw new Error('Binary chunk failed: '+f.path+' #'+i+' length '+data.length+' expected '+expected);
      return data;
    }));
    for(const result of batch) {
      if(result.status!=='fulfilled') throw result.reason;
      encoded+=result.value;
    }
  }
  const b=payload(await tools.mcp__codex_apps__github_create_blob({repository_full_name:repo,encoding:'base64',content:encoded}));
  if (!b.sha) throw new Error('Missing blob SHA');
  entries.push({path:f.path,mode:'100644',type:'blob',sha:b.sha});
  text('Uploaded '+f.path);
}
const tree=payload(await tools.mcp__codex_apps__github_create_tree({repository_full_name:repo,base_tree_sha:commit.tree.sha,tree_elements:entries}));
const next=payload(await tools.mcp__codex_apps__github_create_commit({repository_full_name:repo,parent_sha:parent,tree_sha:tree.sha,message:files.message}));
const current=JSON.parse(payload(await tools.mcp__codex_apps__github_fetch({url:api+'/git/ref/heads/'+encodeURIComponent(branch)})).content);
if(current.object.sha!==parent) throw new Error('Branch changed during upload; rerun to preserve the new work.');
payload(await tools.mcp__codex_apps__github_update_ref({repository_full_name:repo,branch_name:branch,sha:next.sha,force:false}));
text('https://github.com/'+repo+'/blob/'+encodeURIComponent(branch)+'/'+files.journal.split('/').map(encodeURIComponent).join('/'));
text('Published commit '+next.sha);
