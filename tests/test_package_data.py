"""The JSON schema must ship inside the installed package, not only in the source tree.

A plain `pip install .` (no -e) is what the CI smoke job and end users run; before this
test the schema was missing from that install and `rigmarket validate` failed.
"""
import importlib.resources as resources


def test_pack_schema_is_installed_package_data():
    names = {p.name for p in resources.files("rigmarket").iterdir()}
    assert "pack.schema.json" in names
