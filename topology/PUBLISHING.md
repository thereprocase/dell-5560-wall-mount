# Progress publishing

The journal is on the `cloud-topo` branch:
https://github.com/thereprocase/dell-5560-wall-mount/blob/cloud-topo/topology/JOURNAL.md

## One action in Codex

Run `publish_progress.js` in the `functions.exec` JavaScript environment with
`tools`, `store`, `text`, and a `progress` object supplied as arguments. It prepares
the entry, uploads the specified files using the connected GitHub app, commits
them together, and prints the URL to paste directly into chat. This is an agent
command, not an added ChatGPT interface button or a scheduled background job.

Example `progress`:

```json
{
  "title": "Layer-aware PETG recheck",
  "noteFile": "/tmp/progress-note.md",
  "images": ["topology/slot_up/near_wall/results/v30_supported.png"],
  "include": ["topology/slot_up/near_wall/results/screening.json"]
}
```

Use a new image filename for a changed image so old entries retain their original
illustrations. Updates are explicit actions during the conversation. Post the
bare journal URL after successful publication. Never claim an unpublished entry
is live. The publishing script reads the current remote parent, preserves its
tree, checks for concurrent edits, and updates without force. The connected app
supplies authentication; no credentials are stored in this repository.

## Authenticated local Git

```bash
python topology/journal.py --title 'Progress update' --note-file /tmp/note.md \
  --image topology/slot_up/near_wall/results/live.png --push
```

Without `--push`, this prepares the journal and an explicit file manifest only.
`publish_in_cloud.js` can publish that manifest independently. The local Git
command expects a normal branch synchronized with the remote; it does not repair
diverged history or force-push. Change the workspace root in the cloud scripts
when moving the checkout to a different workspace.
