/* Run in Codex functions.exec with tools available. Reads the prepared manifest,
 * publishes through the connected GitHub app, and returns the journal URL.
 * No credentials in files; no force pushes. A concurrent branch edit aborts.
 */
const root = '/workspace/scratch/b0c00b792513/mount-review';
const repo = 'thereprocase/dell-5560-wall-mount';
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
const files = await readJson(`python3 - <<'PY'
import json,base64
from pathlib import Path
r=Path.cwd();m=json.loads((r/'topology/publish_manifest.json').read_text())
out=[]
for name in dict.fromkeys(m['paths']):
 p=(r/name).resolve();p.relative_to(r)
 if not p.is_file():raise FileNotFoundError(p)
 out.append({'path':name,'content':base64.b64encode(p.read_bytes()).decode()})
print(json.dumps({'message':m['message'],'files':out}))
PY`);
const ref = JSON.parse(payload(await tools.mcp__codex_apps__github_fetch({url:api+'/git/ref/heads/cloud-topo'})).content);
const parent = ref.object.sha;
const commit = JSON.parse(payload(await tools.mcp__codex_apps__github_fetch({url:api+'/git/commits/'+parent})).content);
const entries=[];
for (const f of files.files) {
  const b=payload(await tools.mcp__codex_apps__github_create_blob({repository_full_name:repo,encoding:'base64',content:f.content}));
  if (!b.sha) throw new Error('Missing blob SHA');
  entries.push({path:f.path,mode:'100644',type:'blob',sha:b.sha});
}
const tree=payload(await tools.mcp__codex_apps__github_create_tree({repository_full_name:repo,base_tree_sha:commit.tree.sha,tree_elements:entries}));
const next=payload(await tools.mcp__codex_apps__github_create_commit({repository_full_name:repo,parent_sha:parent,tree_sha:tree.sha,message:files.message}));
const current=JSON.parse(payload(await tools.mcp__codex_apps__github_fetch({url:api+'/git/ref/heads/cloud-topo'})).content);
if(current.object.sha!==parent) throw new Error('Branch changed during upload; rerun to preserve the new work.');
payload(await tools.mcp__codex_apps__github_update_ref({repository_full_name:repo,branch_name:'cloud-topo',sha:next.sha,force:false}));
store('slot_remote_base',{commit:next.sha,tree:tree.sha});
text('https://github.com/'+repo+'/blob/cloud-topo/topology/JOURNAL.md');
text('Published commit '+next.sha);
