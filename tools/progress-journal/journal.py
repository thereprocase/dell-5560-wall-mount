#!/usr/bin/env python3
"""Portable Markdown progress journal. Python standard library; Git optional for publishing."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import quote


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def repo_path(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    path.relative_to(root)  # Reject traversal and symlinks escaping the repository.
    return path


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix=path.name + '.', delete=False) as f:
        f.write(content)
        temporary = Path(f.name)
    temporary.replace(path)


def prepare(root: Path, title: str, note: str, images: list[str], includes: list[str],
            journal: str, entries: str, manifest: str, branch: str | None = None) -> dict:
    root = root.resolve()
    journal_path, entries_path, manifest_path = [repo_path(root, p) for p in (journal, entries, manifest)]
    if len({journal_path, entries_path, manifest_path}) != 3:
        raise ValueError('Journal, entries and manifest must be different files')
    if not title.strip() or '\n' in title or '\r' in title:
        raise ValueError('Title must be a nonempty single line')
    images = list(dict.fromkeys(relative(root, repo_path(root, p)) for p in images))
    includes = list(dict.fromkeys(relative(root, repo_path(root, p)) for p in includes))
    for name in images + includes:
        if not repo_path(root, name).is_file():
            raise FileNotFoundError(name)
    previous = json.loads(entries_path.read_text()) if entries_path.exists() else []
    if not isinstance(previous, list):
        raise ValueError('Entries JSON must contain a list')
    entry = {'utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
             'title': title, 'note': note.rstrip(), 'images': images}
    history = [entry, *previous]
    lines = ['# Progress journal', '', 'Latest update first.', '']
    for item in history:
        lines.extend(['## ' + item['title'], '', item['utc'], '', item['note'], ''])
        for name in item['images']:
            image_path = repo_path(root, name)
            link = quote(os.path.relpath(image_path, journal_path.parent).replace(os.sep, '/'), safe='/')
            lines.extend(['![Progress image](' + link + ')', ''])
    paths = list(dict.fromkeys([relative(root, journal_path), relative(root, entries_path), *images, *includes]))
    result = {'schema_version': 1, 'message': title, 'paths': paths,
              'journal': relative(root, journal_path)}
    if branch:
        result['branch'] = branch
    write_atomic(entries_path, json.dumps(history, indent=2, ensure_ascii=False) + '\n')
    write_atomic(journal_path, '\n'.join(lines))
    write_atomic(manifest_path, json.dumps(result, indent=2) + '\n')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.', help='Git repository root; never stored in the journal')
    parser.add_argument('--title', required=True)
    parser.add_argument('--note-file', required=True, help='Markdown body; included verbatim')
    parser.add_argument('--image', action='append', default=[], help='Repository-relative path; repeatable')
    parser.add_argument('--include', action='append', default=[], help='Extra publication path; repeatable')
    parser.add_argument('--journal', default='docs/journal.md')
    parser.add_argument('--entries', default='docs/journal.entries.json')
    parser.add_argument('--manifest', default='.journal/publish.json')
    parser.add_argument('--branch', help='Explicit destination; otherwise current branch for local push')
    parser.add_argument('--push', action='store_true', help='Commit the listed files and push using existing Git authentication')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if Path(git(root, 'rev-parse', '--show-toplevel')).resolve() != root:
        parser.error('--root must be the repository root')
    branch = args.branch
    if args.push:
        current = git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD')
        branch = branch or current
        if branch != current:
            parser.error('--push requires the destination branch to be checked out')
        git(root, 'check-ref-format', '--branch', branch)
    result = prepare(root, args.title, Path(args.note_file).read_text(), args.image,
                     args.include, args.journal, args.entries, args.manifest, branch)
    if args.push:
        git(root, 'add', '--', *result['paths'])
        # --only excludes unrelated changes already staged by the caller.
        git(root, 'commit', '--only', '-m', args.title, '--', *result['paths'])
        git(root, 'push', 'origin', 'HEAD:refs/heads/' + branch)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
