# Publishing spiderswitch

## Install channels

| Channel | Command | When to use |
|---------|---------|-------------|
| **PyPI** (recommended) | `pip install spiderswitch` | After the version is published to PyPI |
| **GitHub Release wheel** | `pip install https://github.com/ailib-official/spiderswitch/releases/download/v0.7.0/spiderswitch-0.7.0-py3-none-any.whl` | Before PyPI publish or air-gapped mirror |
| **Local wheel** | `pip install dist/spiderswitch-<version>-py3-none-any.whl` | Developer / CI artifact |
| **Source** | `pip install -e .` | Active development |

> **Note:** `pip install spiderswitch` resolves from [PyPI](https://pypi.org/project/spiderswitch/). A GitHub Release alone does **not** update PyPI — you must upload the wheel/sdist separately.

## Release checklist

1. Bump `version` in `pyproject.toml` and `packaging/plugin-market/manifest.json`.
2. Update `CHANGELOG.md`.
3. Run tests: `pytest && ruff check src tests && mypy src`
4. Build artifacts:
   ```bash
   python -m build
   bash scripts/package_plugin_bundle.sh
   bash scripts/package_release.sh
   ```
5. Commit, tag, push:
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin main --tags
   ```
6. Create GitHub Release (attach wheel + pro-pack zip).
7. **Publish to PyPI** (pick one):
   - **CI (recommended):** add repository secret `PYPI_API_TOKEN`, then publish the GitHub Release (workflow `.github/workflows/publish-pypi.yml` runs automatically), or run the workflow manually.
   - **Manual:** `bash scripts/publish_pypi.sh` with `TWINE_USERNAME=__token__` and `TWINE_PASSWORD`.
8. Verify:
   ```bash
   pip install --upgrade spiderswitch==X.Y.Z
   spiderswitch version
   ```

## PyPI credentials

The PyPI project owner is currently `hiddenpath`. To publish as `ailib-official`:

1. Obtain a PyPI API token with upload scope for `spiderswitch`.
2. Add it to GitHub → Settings → Secrets → Actions as `PYPI_API_TOKEN`.
3. (Optional) Configure [Trusted Publishers](https://docs.pypi.org/trusted-publishers/) for OIDC-based uploads without long-lived tokens.

## Publishing 0.7.0 (one-time catch-up)

PyPI latest before 0.7.0 was **0.4.2**. After configuring `PYPI_API_TOKEN`:

```bash
git checkout v0.7.0
bash scripts/publish_pypi.sh
```

Or re-publish the GitHub Release to trigger CI, or use **Actions → Publish to PyPI → Run workflow**.
