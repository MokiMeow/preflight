# Third-party notices and license status

`dependency-inventory.json` records the exact Python and npm packages installed in the documented
Windows probe checkout, including versions, raw installed license metadata, npm integrity values,
and the SHA-256 of both lockfiles. Regenerate it only after `uv sync --locked` and
`npm ci --ignore-scripts --no-audit --no-fund` complete successfully:

```bash
uv run python scripts/generate_dependency_inventory.py
uv run python scripts/generate_dependency_inventory.py --check
```

The inventory is a build input for final SBOM/license review. `NOASSERTION`, a classifier-only
record, or missing installed metadata requires review against the distributed package before
publication. It does not change a dependency's license.

## pglast

The installed `pglast 8.4` metadata declares `GPL-3.0-or-later`. Preserve that declaration and the
upstream notices when redistributing a build that contains it. Upstream source and license history:

- <https://github.com/lelit/pglast>
- <https://spdx.org/licenses/GPL-3.0-or-later.html>

Do not describe the entire Preflight repository as MIT merely because TrueForge and many other
dependencies use MIT. The project itself has no selected license in this checkout; its inventory
entry and repository status remain `UNDECIDED` until the team makes that decision and adds the
corresponding license file.

## TrueForge

The exact installed `@truefoundry/trueforge 0.2.1` package declares MIT in its package metadata.
Its transitive dependencies retain their own licenses and integrity values in the generated
inventory. The package lock, inventory, and notices should travel together in a submission bundle.
