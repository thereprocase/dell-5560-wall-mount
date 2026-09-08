/* Arguments: tools, store, text, progress. One prepare-and-publish action. */
const root='/workspace/scratch/b0c00b792513/mount-review';
const quote=s=>"'"+String(s).replace(/'/g,"'\\''")+"'";
const args=['python3','topology/journal.py','--title',progress.title,'--note-file',progress.noteFile];
for(const f of progress.images||[]) args.push('--image',f);
for(const f of progress.include||[]) args.push('--include',f);
const prep=await tools.exec_command({cmd:args.map(quote).join(' '),workdir:root,max_output_tokens:1000});
if(prep.exit_code!==0) throw new Error(prep.output);
const source=await tools.exec_command({cmd:'cat topology/publish_in_cloud.js',workdir:root,max_output_tokens:6000});
if(source.exit_code!==0) throw new Error(source.output);
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
await new AsyncFunction('tools','store','text',source.output)(tools,store,text);
