# Repository agent skills

This integration was reconstructed from the user-provided `GOODPRACTICE(1).md`
and `nexprompt.md` attachments and the two requested GitHub repositories. The
previously prepared `nexawork_agent_setup.zip` was unavailable. It is not a
byte-for-byte recreation of that archive.

## Contents and provenance

- `AGENTS.md`: scoped instructions for the existing backend and future UI work.
- `GOODPRACTICE.md`: supplied engineering policy with an evidence-based project
  profile; unknown production decisions remain explicit.
- `NEXAWORK_PRODUCT_SPEC.md`: supplied product vision, preserved as context.
- `.agents/skills/rpi-production-engineering/`: complete tracked package from
  <https://github.com/maxchichar/rpi-production-engineering> at commit
  `dc3e9278e974c5507557b31a7868223d1a7dabd2` (Apache-2.0).
- `.agents/skills/interface-forge/`: complete tracked package from
  <https://github.com/maxchichar/interface-forge> at commit
  `da70c1ca8869c10f0cf3e64ad90abf324a37da6a` (MIT).

Upstream files, licenses, scripts, references, examples, and tests are unchanged.
They are vendored as ordinary files, with executable modes preserved. No nested
Git repositories, submodules, global agent installations, or runtime dependencies
are added. Skills are guidance; discovery and reload behavior depends on the agent.

## Verify or restore

Run from the repository root (Python 3.12; installer uses only the standard library):

```sh
# Offline integrity check: exact inventory, SHA-256 contents and executable modes.
python3 scripts/install_agent_skills.py --check

# Restore missing packages from pinned GitHub commits; requires git and network.
python3 scripts/install_agent_skills.py

# Or restore from local upstream package directories under /path/to/sources/.
python3 scripts/install_agent_skills.py --source-root /path/to/sources
```

The lock file `.agents/skills.lock.json` records every installed file and its
upstream commit. Existing matching packages are left alone; an existing modified,
incomplete, or symlinked package causes an error before restoration begins.
The installer never automatically overwrites a package. Generated Python caches
are ignored by the integrity check. Commit restoration results as normal files.

To update a skill, review a specific upstream commit, regenerate that package's
file hashes and modes in the lock, replace its vendored contents, and run all
checks below in a feature branch. Review lock changes together with package
changes; this lock detects drift, not a maliciously rewritten lock.

## Validation

```sh
python3 scripts/install_agent_skills.py --check
python3 -m unittest discover -s tests/scripts -p test_install_agent_skills.py -v
python3 .agents/skills/rpi-production-engineering/scripts/validate_skill.py
python3 -m unittest discover -s .agents/skills/rpi-production-engineering/scripts -p test_rpi.py -v
python3 .agents/skills/interface-forge/scripts/validate_skill.py
python3 -m unittest discover -s .agents/skills/interface-forge/tests -v
git diff --check
```

These validate package integrity and helper behavior. They do not establish app
security, production readiness, UI quality, accessibility, or full application
test success. The existing application CI remains responsible for its dependency
audit, PostgreSQL migrations, and application tests.
