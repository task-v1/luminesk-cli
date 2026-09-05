"""Unified, serializable preview shown before an installation mutates state."""

from __future__ import annotations

import json
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
        ownership = self.capabilities["ownership"]
        lines = [
            "Install preview",
            f"  Trust: {self.trust['classification']} ({self.trust['kind']})",
            f"  Source: {self.trust['source']}",
            f"  Recipe: {self.trust['version']} @ {self.trust['revision']} "
            f"(tracking {'yes' if self.trust['tracking'] else 'no'})",
            f"  Manifest digest: {self.trust['manifestDigest']}",
            f"  Template digest: {self.trust['templateDigest'] or 'none'}",
            f"  Target platform: {self.capabilities['targetPlatform']}",
            f"  Runtime image: {runtime['image']}",
            "  Runtime command: " + json.dumps(runtime["command"], ensure_ascii=False),
            f"  Runtime memory: {runtime['memory'] or 'not limited'}",
            f"  Runtime user: {runtime['runAs'] or 'image default'}",
            f"  Read-only root: {'yes' if runtime['readOnlyRoot'] else 'no'}",
            f"  Build: {'enabled' if build['enabled'] else 'disabled'} "
            f"(network {'enabled' if build['network'] else 'disabled'})",
            "  Build images: "
            + (
                ", ".join(f"{name}={image}" for name, image in build["images"].items())
                or "none"
            ),
            "  Resolved artifacts:",
        ]
        if sources:
            for source in sources:
                lines.extend(
                    (
                        f"    {source['id']}: {source['type']} {source['version']} "
                        f"@ {source['sourceRevision']}",
                        f"      URL: {source['url']}",
                        f"      Digest: {source['digest']}",
                        f"      Size/media: {source['size']} bytes / "
                        f"{source['mediaType'] or 'unspecified'}",
                        f"      Target: {source['target']}",
                    )
                )
        else:
            lines.append("    none")
        lines.append("  Mounts:")
        lines.extend(
            (
                f"    {mount['source']} -> {mount['target']} ({mount['mode']})"
                for mount in runtime["mounts"]
            )
            if runtime["mounts"]
            else ("    none",)
        )
        lines.append("  Ports:")
        lines.extend(
            (
                f"    {port['name']}: {port['host']}:{port['container']}"
                f"/{port['protocol']}"
                for port in runtime["ports"]
            )
            if runtime["ports"]
            else ("    none",)
        )
        lines.append("  Template files:")
        lines.extend(
            (f"    {path}" for path in self.capabilities["templateFiles"])
            if self.capabilities["templateFiles"]
            else ("    none",)
        )
        lines.extend(
            (
                "  Ownership preserve: " + (", ".join(ownership["preserve"]) or "none"),
                "  Ownership data: " + (", ".join(ownership["data"]) or "none"),
                "  Ownership executable: "
                + (", ".join(ownership["executable"]) or "none"),
                "  Checks:",
            )
        )
        lines.extend(
            (
                f"    {check['id']}: {check['phase']}/{check['kind']} "
                f"({'required' if check['required'] else 'optional'})"
                for check in self.capabilities["checks"]
            )
            if self.capabilities["checks"]
            else ("    none",)
        )
        lines.extend(
            (
                f"  Requires downtime: {'yes' if self.plan.requires_downtime else 'no'}",
                "  Downloads: " + (", ".join(self.plan.downloads) or "none"),
                "  Warnings: " + (", ".join(self.plan.warnings) or "none"),
            )
        )
        lines.append(f"  Changes ({len(self.plan.changes)}):")
        if self.plan.changes:
            lines.extend(
                f"    {change.action:8} {change.path} — {change.reason}"
                for change in self.plan.changes
            )
        else:
            lines.append("    none")
        return "\n".join(lines)
