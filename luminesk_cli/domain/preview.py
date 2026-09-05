"""Unified, serializable preview shown before an installation mutates state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from luminesk_cli.domain.lockfile import Lockfile
from luminesk_cli.domain.plan import Plan
from luminesk_cli.domain.recipe import RecipeSnapshot


@dataclass(slots=True, frozen=True)
class Preview:
    trust: dict[str, Any]
    capabilities: dict[str, Any]
    plan: Plan

    @classmethod
    def for_install(
        cls,
        snapshot: RecipeSnapshot,
        lockfile: Lockfile,
        plan: Plan,
    ) -> Preview:
        manifest = snapshot.manifest
        origin = snapshot.origin
        template_files = [
            entry.path
            for entry in snapshot.entries
            if entry.type == "file"
            and manifest.template is not None
            and (
                entry.path == manifest.template
                or entry.path.startswith(f"{manifest.template}/")
            )
        ]
        return cls(
            trust={
                "classification": {
                    "database": "official",
                    "github": "direct",
                    "local": "local",
                }[origin.kind],
                "kind": origin.kind,
                "source": origin.source,
                "revision": origin.revision,
                "version": origin.version,
                "tracking": origin.tracking,
                "manifestDigest": origin.manifest_digest,
                "templateDigest": origin.template_digest,
            },
            capabilities={
                "targetPlatform": lockfile.target,
                "sources": [
                    {
                        "id": source_id,
                        "type": source.type,
                        "version": source.version,
                        "sourceRevision": source.source_revision,
                        "url": source.url,
                        "size": source.size,
                        "digest": source.digest,
                        "target": source.target,
                        "mediaType": source.media_type,
                    }
                    for source_id, source in sorted(lockfile.sources.items())
                ],
                "runtime": {
                    "image": lockfile.runtime.image,
                    "command": list(manifest.runtime.command),
                    "memory": manifest.runtime.memory,
                    "runAs": manifest.runtime.run_as,
                    "readOnlyRoot": manifest.runtime.read_only_root,
                    "mounts": [
                        {
                            "source": mount.source,
                            "target": mount.target,
                            "mode": mount.mode,
                        }
                        for mount in manifest.runtime.mounts
                    ],
                    "ports": [
                        {
                            "name": port.name,
                            "host": port.host,
                            "container": port.container,
                            "protocol": port.protocol,
                        }
                        for port in manifest.runtime.ports
                    ],
                },
                "build": {
                    "enabled": lockfile.build is not None,
                    "network": manifest.build.network if manifest.build else False,
                    "images": (
                        dict(sorted(lockfile.build.images.items()))
                        if lockfile.build
                        else {}
                    ),
                },
                "templateFiles": template_files,
                "ownership": {
                    "preserve": list(manifest.ownership.preserve),
                    "data": list(manifest.ownership.data),
                    "executable": list(manifest.ownership.executable),
                },
                "checks": [
                    {
                        "id": check.id,
                        "phase": check.phase,
                        "kind": check.kind,
                        "required": check.required,
                    }
                    for check in manifest.checks
                ],
            },
            plan=plan,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trust": self.trust,
            "capabilities": self.capabilities,
            "plan": {
                "operation": self.plan.operation,
                "target": self.plan.target,
                "changes": [
                    {
                        "action": change.action,
                        "path": change.path,
                        "reason": change.reason,
                        "digest": change.digest,
                    }
                    for change in self.plan.changes
                ],
                "downloads": list(self.plan.downloads),
                "warnings": list(self.plan.warnings),
                "requiresDowntime": self.plan.requires_downtime,
            },
        }

    def to_text(self) -> str:
        sources = self.capabilities["sources"]
        runtime = self.capabilities["runtime"]
        build = self.capabilities["build"]
        lines = [
            "Install preview",
            f"  Trust: {self.trust['classification']} ({self.trust['source']})",
            f"  Recipe: {self.trust['version']} @ {self.trust['revision']}",
            f"  Manifest: {self.trust['manifestDigest']}",
            f"  Target platform: {self.capabilities['targetPlatform']}",
            f"  Runtime image: {runtime['image']}",
            f"  Runtime user: {runtime['runAs'] or 'image default'}",
            f"  Read-only root: {'yes' if runtime['readOnlyRoot'] else 'no'}",
            f"  Build: {'enabled' if build['enabled'] else 'disabled'} "
            f"(network {'enabled' if build['network'] else 'disabled'})",
            "  Resolved artifacts:",
        ]
        if sources:
            lines.extend(
                f"    {source['id']}: {source['type']} {source['version']} "
                f"({source['digest']}) -> {source['target']}"
                for source in sources
            )
        else:
            lines.append("    none")
        lines.append(f"  Changes ({len(self.plan.changes)}):")
        if self.plan.changes:
            lines.extend(
                f"    {change.action:8} {change.path} — {change.reason}"
                for change in self.plan.changes
            )
        else:
            lines.append("    none")
        return "\n".join(lines)
