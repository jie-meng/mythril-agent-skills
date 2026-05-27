"""Shared assets bundled into individual skills.

Files under this package are the **canonical source** for assets that
must be duplicated into multiple skill directories (because each skill
is installed independently and must be self-contained).

Sync to all consumers via:

    python3 scripts/sync-shared-assets.py

The drift test (tests/test_shared_assets_sync.py) verifies bundled
copies stay byte-identical to the canonical source.
"""
