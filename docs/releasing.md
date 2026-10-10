# Releasing to PyPI

Releases are published by GitHub Actions using PyPI
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/), so no API
tokens are stored anywhere.

## One-time setup

1. **PyPI.** Log in at [pypi.org](https://pypi.org), go to *Your projects →
   Publishing → Add a new pending publisher* and enter:
    - PyPI project name: `liander-open-data`
    - Owner: `lingkang95`
    - Repository: `Liander_open_data`
    - Workflow: `publish.yml`
    - Environment: `pypi`
2. **TestPyPI (optional).** Do the same on [test.pypi.org](https://test.pypi.org)
   with environment `testpypi`.
3. **GitHub.** Under *Settings → Environments*, create the environments `pypi`
   and `testpypi`. Adding required reviewers to `pypi` is recommended.

## Cutting a release

1. Update `version` in `pyproject.toml` (semantic versioning).
2. Move the changelog entries to a new version heading in `CHANGELOG.md`.
3. Check locally:

    ```bash
    uv run pytest
    uv build                  # creates dist/*.whl and dist/*.tar.gz
    uvx twine check dist/*
    ```

4. Commit, tag and push:

    ```bash
    git commit -am "Release 0.2.0"
    git tag v0.2.0
    git push origin master --tags
    ```

5. Create a GitHub release from the tag. The **publish** workflow builds
   the package and uploads it to PyPI.

To try the pipeline first, run the *publish* workflow manually
(*Actions → publish → Run workflow*). This uploads to TestPyPI only.

## Manual upload (fallback)

```bash
uv build
uv publish            # prompts for a PyPI API token
```

## What goes into the package

The wheel contains only `src/liander_open_data`, including the bundled
dictionary (~270 kB). The `data/` directory with the profile CSVs is
**never** packaged: it is excluded from the sdist in `pyproject.toml` and
listed in `.gitignore`.
