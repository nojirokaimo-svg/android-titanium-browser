#!/usr/bin/env python3
"""Restore source timestamps without hiding edits or touching Ninja outputs.

New caches carry hashes and source mtimes. The one legacy completed cache is
bootstrapped from verified feature hashes; unknown caches are never guessed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
AGE_NS = 946684800 * 10**9
STATE = "kiwi-source-state.json"
PLAN = "kiwi-incremental-plan.json"


def digest(path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def checked_path(source, name):
    p = Path(name)
    if p.is_absolute() or '..' in p.parts or 'out' in p.parts or '.git' in p.parts:
        raise RuntimeError(f'Invalid source path: {name}')
    result = source / p
    if result.is_symlink():
        raise RuntimeError(f'Patch-owned symlink is unsupported: {name}')
    return result


def restore(source, cache_key, manifest, legacy, identity):
    out = source / 'out/Default'
    state_path = out / STATE
    if state_path.is_file():
        previous = json.loads(state_path.read_text())
        if previous['identity'] != identity:
            raise RuntimeError('Cache source/toolchain identity changed; preserving cache and stopping')
        previous = previous['files']
    else:
        if cache_key != legacy['cache_key']:
            raise RuntimeError('No source provenance for this cache; preserving cache and stopping')
        previous = {p: {'sha256': h, 'mtime_ns': AGE_NS} for p, h in legacy['files'].items()}
    names = sorted(set(manifest['files']) | set(previous))
    paths = {name: checked_path(source, name) for name in names}
    current = {name: digest(p) for name, p in paths.items()}
    # Age only source files. Prune every out/.git directory, including nested
    # dependency repositories; never alter .ninja_log or compiled objects.
    for directory, dirs, files in os.walk(source):
        dirs[:] = [d for d in dirs if d not in ('.git', 'out') and not (Path(directory)/d).is_symlink()]
        for name in files:
            p = Path(directory) / name
            if name != '.git' and not p.is_symlink():
                os.utime(p, ns=(AGE_NS, AGE_NS))
    now = time.time_ns()
    changed = []
    records = {}
    for name, p in paths.items():
        old = previous.get(name)
        different = old is None or old['sha256'] != current[name]
        stamp = now if different else old['mtime_ns']
        if different:
            changed.append(name)
        if p.is_file():
            os.utime(p, ns=(stamp, stamp))
        records[name] = {'sha256': current[name], 'mtime_ns': stamp}
    # This new metadata travels with the NEXT immutable cache archive. On a
    # time-sliced continuation, retain changed-source mtimes instead of touching
    # those files again and rebuilding the same dependencies each stage.
    state_path.write_text(json.dumps({'identity': identity, 'files': records}, indent=2) + '\n')
    plan = {
        'cache_key': cache_key,
        'identity': identity,
        'changed_sources': changed,
        'tracked_sources': len(records),
    }
    # The build step consumes this report before Ninja starts.  It is stored in
    # out/Default so a checkpoint continuation can prove whether this stage
    # introduced source edits without touching any compiled output.
    (out / PLAN).write_text(json.dumps(plan, indent=2) + '\n')
    print(json.dumps(plan, indent=2))
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--cache-key', required=True)
    parser.add_argument('--identity', required=True)
    args = parser.parse_args()
    restore(args.source.resolve(), args.cache_key,
            json.loads((HERE/'manifest.json').read_text()),
            json.loads((HERE/'legacy-cache-source-hashes.json').read_text()), args.identity)


if __name__ == '__main__':
    main()
