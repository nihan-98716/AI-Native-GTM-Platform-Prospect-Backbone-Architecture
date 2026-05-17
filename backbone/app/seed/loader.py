from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import User
from app.models.tenant import Tenant


@dataclass(frozen=True)
class SeedManifest:
    tenant_slug: str
    files: dict[str, str]


class SeedLoader:
    def __init__(self, seed_dir: str) -> None:
        self._seed_dir = Path(seed_dir)

    def _load_yaml(self, path: Path) -> list[dict] | dict:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or []
        return data

    def load_manifest(self) -> SeedManifest:
        manifest_path = self._seed_dir / "seed_manifest.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Missing seed manifest: {manifest_path}")
        raw = self._load_yaml(manifest_path)
        if not isinstance(raw, dict):
            raise ValueError("seed_manifest.yaml must contain an object.")
        tenant_slug = raw.get("tenant_slug")
        files = raw.get("files")
        if not tenant_slug or not isinstance(files, dict):
            raise ValueError("seed_manifest.yaml must define tenant_slug and files map.")
        for logical_name, rel_path in files.items():
            file_path = self._seed_dir / rel_path
            if not file_path.exists():
                raise FileNotFoundError(f"Missing seed file '{logical_name}': {file_path}")
        return SeedManifest(tenant_slug=tenant_slug, files=files)

    def seed(self, session: Session) -> dict[str, int]:
        manifest = self.load_manifest()
        tenants = self._load_yaml(self._seed_dir / manifest.files["tenants"])
        users = self._load_yaml(self._seed_dir / manifest.files["users"])
        if not isinstance(tenants, list) or not isinstance(users, list):
            raise ValueError("Seed tenants/users files must contain arrays.")

        tenant = session.execute(
            select(Tenant).where(Tenant.slug == manifest.tenant_slug)
        ).scalar_one_or_none()
        if tenant is None:
            tenant_name = next((item.get("name") for item in tenants if item.get("slug") == manifest.tenant_slug), manifest.tenant_slug)
            tenant = Tenant(name=tenant_name, slug=manifest.tenant_slug)
            session.add(tenant)
            session.flush()

        created_users = 0
        for item in users:
            if item.get("tenant_slug") != manifest.tenant_slug:
                continue
            email = item.get("email")
            if not email:
                continue
            existing = session.execute(
                select(User).where(User.tenant_id == tenant.id, User.email == email)
            ).scalar_one_or_none()
            if existing:
                continue
            session.add(
                User(
                    tenant_id=tenant.id,
                    email=email,
                    full_name=item.get("full_name", email),
                    status="active",
                    roles=item.get("roles", []),
                    permissions=item.get("permissions", {}),
                )
            )
            created_users += 1

        return {"tenants": 1, "users_created": created_users}

