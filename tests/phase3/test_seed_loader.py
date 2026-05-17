from pathlib import Path

import pytest
import yaml

from app.seed.loader import SeedLoader


def write_yaml(path: Path, payload) -> None:
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")


def test_seed_loader_requires_manifest_files_to_exist(tmp_path: Path):
    write_yaml(
        tmp_path / "seed_manifest.yaml",
        {
            "tenant_slug": "acme-demo",
            "files": {"tenants": "tenants.yaml", "users": "users.yaml"},
        },
    )
    write_yaml(tmp_path / "tenants.yaml", [{"slug": "acme-demo", "name": "Acme"}])

    loader = SeedLoader(seed_dir=str(tmp_path))
    with pytest.raises(FileNotFoundError):
        loader.load_manifest()


def test_seed_loader_loads_manifest_when_files_present(tmp_path: Path):
    write_yaml(
        tmp_path / "seed_manifest.yaml",
        {
            "tenant_slug": "acme-demo",
            "files": {"tenants": "tenants.yaml", "users": "users.yaml"},
        },
    )
    write_yaml(tmp_path / "tenants.yaml", [{"slug": "acme-demo", "name": "Acme"}])
    write_yaml(tmp_path / "users.yaml", [{"tenant_slug": "acme-demo", "email": "owner@acme.test"}])

    loader = SeedLoader(seed_dir=str(tmp_path))
    manifest = loader.load_manifest()
    assert manifest.tenant_slug == "acme-demo"
