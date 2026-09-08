# Portable progress journal

Copy this directory into another Git repository. It has no third-party Python dependencies and contains no project identity, account names, credentials, personal notes or hardcoded workspace paths.

The tool records only the title, UTC time, Markdown note and image paths you supply. It creates a latest-first Markdown journal, JSON history and an explicit publication manifest. It does not collect system details, usernames, environment variables, Git author identity or remote URLs. Notes and image contents are included as supplied; it is **not an automatic PII scrubber**. Git/GitHub commits use the caller's normal account metadata.

## Prepare an entry locally

Run from the repository root; the note can live outside the repository:

```sh
python tools/progress-journal/journal.py \
  --title 'Curved frame review' --note-file /tmp/review-note.md \
  --image artifacts/frame-review.png --include artifacts/validation.json
```

Defaults are `docs/journal.md`, `docs/journal.entries.json` and `.journal/publish.json`. Override them with `--journal`, `--entries` and `--manifest`. All publication paths must stay inside the repository; traversal and escaping symlinks are rejected. Markdown image URLs are relative to the journal and support spaces in filenames.

Use a new image filename when its contents change, preserving historical entries. Notes are ordinary Markdown: write any relative links relative to the journal's location. Explicitly include additional files you want to publish. The manifest itself is local bookkeeping and is not automatically committed.

## Publish with local Git

Add `--push` to prepare, stage the explicit file list, commit it and push the current branch to `origin`. Supply `--branch topic-branch` to require a specific checked-out branch. Existing Git authentication is used; credentials are never accepted or stored by the tool. Unrelated staged changes are excluded from the commit. Pushes are ordinary pushes without force.

If a push fails, the local journal and commit remain for inspection/retry. A non-fast-forward push fails normally; reconcile the branch before retrying. Preparing without `--push` performs no remote write.

## Publish through a connected GitHub tool

`publish.js` is a portable async function body for an agent runtime that supplies `tools`, `text` and a `config` object. It reads the manifest, uploads the exact files, creates one commit and returns the journal URL. Supply the absolute workspace root and repository destination at runtime; neither is embedded in the source or written into journal entries.

```js
const config = {
  root: workspaceRoot,
  repository: repositoryFullName, // owner/repository, provided by the caller
  branch: destinationBranch,
  manifest: '.journal/publish.json'
};
// Execute publish.js as an async function with tools, text and config arguments.
```

The adapter expects `exec_command` and connected GitHub `fetch`, `create_blob`, `create_tree`, `create_commit` and `update_ref` tools using the names in the source. Rename those bindings to match another runtime. The branch must already exist. File reads are validated inside the root, binary reads are chunked in parallel batches, the current tree is preserved, and a concurrent branch change aborts publication. The reference update never forces history. Interrupted uploads may leave unattached Git objects but do not delete files.

The local Python command is the universal entry point. The JavaScript file adds the equivalent single publish action for an agent with a connector; it does not create a ChatGPT interface button or a background job.

## Check the scaffold

```sh
python -m unittest discover -s tools/progress-journal -p 'test_*.py'
```

The tests use temporary repositories and files, with no network access or account identity.
