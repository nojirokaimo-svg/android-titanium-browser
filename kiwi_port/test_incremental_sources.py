import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from incremental_sources import AGE_NS, PLAN, STATE, digest, restore


class IncrementalTest(unittest.TestCase):
    def test_100_actions_restore_edit_and_continue(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src = root/'first'
            out = src/'out/Default'
            out.mkdir(parents=True)
            names = [f'input{i}.txt' for i in range(100)]
            for name in names:
                (src/name).write_text(name)
                os.utime(src/name, ns=(AGE_NS, AGE_NS))
            for i, name in enumerate(names):
                p = out/f'output{i}'
                p.write_text(name)
                os.utime(p, ns=(AGE_NS + 1, AGE_NS + 1))
            before = {p.name: (digest(p), p.stat().st_mtime_ns) for p in out.iterdir()}
            legacy = {'cache_key': 'verified-legacy', 'files': {n: digest(src/n) for n in names}}
            fresh = root/'fresh'
            fresh.mkdir()
            shutil.copytree(out, fresh/'out/Default', copy_function=shutil.copy2)
            for name in names:
                (fresh/name).write_text(name)
            (fresh/names[17]).write_text('changed')
            manifest = {'files': dict.fromkeys(names)}
            with contextlib.redirect_stdout(io.StringIO()):
                changed = restore(fresh, 'verified-legacy', manifest, legacy, 'pinned')
            self.assertEqual(changed, [names[17]])
            restored = fresh/'out/Default'
            plan = json.loads((restored/PLAN).read_text())
            self.assertEqual(plan['changed_sources'], [names[17]])
            self.assertEqual(plan['tracked_sources'], 100)
            self.assertEqual(plan['cache_key'], 'verified-legacy')
            for name, data in before.items():
                p = restored/name
                self.assertEqual((digest(p), p.stat().st_mtime_ns), data)
            stale = [i for i, name in enumerate(names)
                     if (fresh/name).stat().st_mtime_ns > (restored/f'output{i}').stat().st_mtime_ns]
            self.assertEqual(stale, [17])
            # Simulate the one-edge rebuild, then verify the next job has zero stale edges.
            (restored/'output17').write_text('changed')
            os.utime(restored/'output17', ns=(changed_stamp := (fresh/names[17]).stat().st_mtime_ns + 1,)*2)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(restore(fresh, 'next', manifest, legacy, 'pinned'), [])
            stale = [i for i, name in enumerate(names)
                     if (fresh/name).stat().st_mtime_ns > (restored/f'output{i}').stat().st_mtime_ns]
            self.assertEqual(stale, [])
            with self.assertRaises(RuntimeError):
                restore(fresh, 'next', manifest, legacy, 'different-upstream')


if __name__ == '__main__':
    unittest.main()
