# Plugin Market Packaging

This directory stores plugin-market packaging metadata for `spiderswitch`.

## Files

- `manifest.json`: plugin metadata, entrypoint, install and health check commands.

## Build release bundle

```bash
bash scripts/package_plugin_bundle.sh
# Output: dist/plugin-market/ (manifest + install scripts + wheel)
```

## Post-install (0.7.0+)

After install, run one-shot setup (includes capability index pre-build):

```bash
spiderswitch setup --client cursor
```

Or manually:

```bash
spiderswitch protocol setup
spiderswitch index build
spiderswitch doctor --json
```

## Validation

```bash
bash scripts/smoke_plugin_check.sh
pytest tests/test_plugin_packaging.py -q
```
