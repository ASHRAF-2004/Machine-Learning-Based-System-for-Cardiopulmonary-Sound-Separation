#!/usr/bin/env python3
"""Check the exported owl GPU mesh, without rendering or changing its assets.

Supports v5 source-specific conforming meshes (float32 positions/flows and
uint32 indices), and the older v4 regular grid (float16 flows). For v4, uses
the actual shader positions [0, 1163] x [0, 600], including the final edge
vertex, rather than the builder's older [0, 1162] x [0, 599] sample positions.
Exported displacements are combined as the vertex shader combines them.

A geometry check is not a visual approval. Occluded surfaces can legitimately
compress. Compression/stretching are reported separately from inversion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIELD = ROOT / "public/assets/owl/smooth-field"
DEFAULT_REPORT = ROOT / "evidence/owl-smooth-v2/surface-geometry.json"

# Fixed before inspecting results. All negative areas remain in the report.
# Float roundoff alone should not fail an otherwise sound export. A visible
# inverted footprint of >= 0.25 source-pixel^2 after blend/alpha weighting is a
# failure; smaller footprints are explicitly reported as subpixel residuals.
INVERSION_EPSILON = 1e-5
VISIBLE_ALPHA = 0.05
OPAQUE_ALPHA = 0.90
SIGNIFICANT_WEIGHTED_AREA = 0.25
FOCUSED_POSES = [
    (0.0, 0.0), (-5.25, -5.46), (-9.75, -10.13), (-15.0, -9.0),
    (-20.0, -12.0), (-21.213203, -12.727922),
    (9.1, 3.15), (16.89, 5.85), (9.75, 10.13),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cross(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def texture_alpha_at_vertices(path: Path, points: np.ndarray) -> np.ndarray:
    """Bilinear clamp sampling matching shader uv=(position+.5)/texture_size."""
    with Image.open(path) as image:
        alpha = np.asarray(image.convert("RGBA"))[:, :, 3].astype(np.float32) / 255
    height, width = alpha.shape
    x = np.clip(points[:, 0], 0, width - 1)
    y = np.clip(points[:, 1], 0, height - 1)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    x1, y1 = np.minimum(x0 + 1, width - 1), np.minimum(y0 + 1, height - 1)
    tx, ty = x - x0, y - y0
    return ((alpha[y0, x0] * (1 - tx) + alpha[y0, x1] * tx) * (1 - ty)
            + (alpha[y1, x0] * (1 - tx) + alpha[y1, x1] * tx) * ty)


def weights_at(poses: np.ndarray, ids: list[int], pose: tuple[float, float]):
    return np.linalg.solve(np.vstack([poses[ids].T, np.ones(3)]), [*pose, 1.0])


def describe_mesh(positions: np.ndarray, triangles: np.ndarray) -> dict:
    """Keep geometry/region ownership local to each actual source mesh."""
    if positions.ndim != 2 or positions.shape[1] != 2 or not np.isfinite(positions).all():
        raise ValueError("Invalid source-mesh positions")
    if triangles.ndim != 2 or triangles.shape[1] != 3 or not len(triangles):
        raise ValueError("Invalid source-mesh triangles")
    if triangles.min() < 0 or triangles.max() >= len(positions):
        raise ValueError("Source-mesh index outside vertex buffer")
    vertices = positions[triangles].astype(np.float64)
    area2 = cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
    centers = vertices.mean(axis=1)
    return {"positions": positions, "triangles": triangles, "base_vertices": vertices,
            "base_area2": area2, "centers": centers,
            "regions": {"upper_head": centers[:, 1] < 350,
                        "neck": (centers[:, 1] >= 350) & (centers[:, 1] < 555),
                        "body_guard": centers[:, 1] >= 555}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--field", type=Path, default=DEFAULT_FIELD)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--steps", type=int, default=8,
                        help="Barycentric subdivisions per pose triangle; default 8 (45 samples each)")
    args = parser.parse_args()
    if args.steps < 2:
        parser.error("--steps must be at least 2")
    field = args.field.resolve()
    manifest_path = field / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    manifest_mtime = manifest_path.stat().st_mtime
    views = {view["id"]: view for view in manifest["views"]}
    if sorted(views) != list(range(len(views))):
        raise ValueError("Expected the contiguous view IDs used by owlSurface.ts")
    poses = np.asarray([[views[i]["yaw"], views[i]["pitch"]] for i in views], float)
    width, height = manifest["width"], manifest["height"]
    if (width, height) != (1163, 600):
        raise ValueError("Current owlSurface.ts shader uses fixed 1163 x 600 dimensions")
    conforming = bool(manifest.get("meshes"))
    meshes, flows, asset_hashes = {}, {}, {}

    def read_binary(descriptor: dict, dtype: str) -> np.ndarray:
        path = field / descriptor["file"]
        compressed = path.read_bytes()
        raw = gzip.decompress(compressed) if path.suffix == ".gz" else compressed
        if descriptor.get("decodedBytes", len(raw)) != len(raw):
            raise ValueError(f"Decoded byte count differs from manifest: {path}")
        if descriptor.get("bytes", len(compressed)) != len(compressed):
            raise ValueError(f"Compressed byte count differs from manifest: {path}")
        asset_hashes[path.name] = hashlib.sha256(compressed).hexdigest()
        return np.frombuffer(raw, dtype=dtype)

    if conforming:
        for description in manifest["meshes"]:
            positions = read_binary(description["positions"], "<f4")
            indices = read_binary(description["indices"], "<u4")
            if positions.size != description["vertexCount"] * 2:
                raise ValueError(f"Position count differs for view {description['id']}")
            if indices.size != description["indexCount"] or indices.size % 3:
                raise ValueError(f"Index count differs for view {description['id']}")
            if description["id"] in meshes:
                raise ValueError(f"Duplicate source mesh {description['id']}")
            meshes[description["id"]] = describe_mesh(positions.reshape(-1, 2), indices.reshape(-1, 3))
        if set(meshes) != set(views):
            raise ValueError("Source meshes do not match the available views")
        representation = {"type": "source-specific conforming meshes", "width": width, "height": height,
                          "flow_type": "float32", "index_type": "uint32", "position_arithmetic": "float32",
                          "alpha_samples_per_triangle": 7}
    else:
        mw, mh = manifest["meshWidth"], manifest["meshHeight"]
        if mw * mh > 65536:
            raise ValueError("Mesh does not fit runtime Uint16 element indices")
        xx, yy = np.meshgrid(np.linspace(0, width, mw), np.linspace(0, height, mh))
        positions = np.column_stack([xx.ravel(), yy.ravel()]).astype(np.float32)
        cells = np.arange(mw * mh).reshape(mh, mw)[:-1, :-1].ravel()
        triangles = np.stack([np.column_stack([cells, cells + 1, cells + mw]),
                              np.column_stack([cells + 1, cells + mw + 1, cells + mw])], axis=1).reshape(-1, 3)
        shared = describe_mesh(positions, triangles)
        meshes = {source_id: shared for source_id in views}
        representation = {"type": "regular grid", "width": width, "height": height,
                          "vertices_x": mw, "vertices_y": mh, "right_bottom_edge": [width, height],
                          "flow_type": "float16", "index_type": "uint16", "position_arithmetic": "float32",
                          "alpha_samples_per_triangle": 3}
    for edge in manifest["edges"]:
        value = read_binary(edge, "<f4" if conforming else "<f2").astype(np.float32)
        if value.size != meshes[edge["from"]]["positions"].size or not np.isfinite(value).all():
            raise ValueError(f"Invalid exported flow: {edge['file']}")
        flows[edge["from"], edge["to"]] = value.reshape(-1, 2)
    alpha_data = {}
    for index, view in views.items():
        mesh = meshes[index]
        positions, triangles = mesh["positions"], mesh["triangles"]
        path = field / view["texture"]
        alpha = texture_alpha_at_vertices(path, positions)[triangles]
        if conforming:
            # A large conforming triangle can cross opaque texture although its
            # vertices are transparent. Include interior/edge samples rather
            # than declaring its entire footprint irrelevant from three points.
            vertices = mesh["base_vertices"]
            extra = np.concatenate([mesh["centers"], (vertices[:, 0] + vertices[:, 1]) * .5,
                                    (vertices[:, 1] + vertices[:, 2]) * .5,
                                    (vertices[:, 2] + vertices[:, 0]) * .5])
            extra_alpha = texture_alpha_at_vertices(path, extra).reshape(4, -1).T
            alpha = np.column_stack([alpha, extra_alpha])
        alpha_data[index] = {"minimum": alpha.min(axis=1), "maximum": alpha.max(axis=1),
                             "mean": alpha.mean(axis=1)}
        asset_hashes[path.name] = sha(path)

    samples = []
    for triangle_index, ids in enumerate(manifest["triangles"]):
        for a in range(args.steps + 1):
            for b in range(args.steps + 1 - a):
                weights = np.array([a, b, args.steps - a - b], float) / args.steps
                pose = weights @ poses[ids]
                samples.append(("barycentric-grid", triangle_index, ids, weights, pose))
    for pose in FOCUSED_POSES:
        for triangle_index, ids in enumerate(manifest["triangles"]):
            weights = weights_at(poses, ids, pose)
            if weights.min() >= -1e-6:
                weights = np.maximum(0, weights)
                weights /= weights.sum()
                samples.append(("focused", triangle_index, ids, weights, np.asarray(pose)))
                break
        else:
            raise ValueError(f"Focused pose outside manifest hull: {pose}")

    rows = []
    global_witnesses = []
    for sample_index, (kind, triangle_index, ids, weights, pose) in enumerate(samples):
        contributors = []
        for slot, source_id in enumerate(ids):
            weight = float(weights[slot])
            if weight < 1e-5:  # Same negligible-contributor skip as runtime draw().
                continue
            mesh = meshes[source_id]
            positions, triangles = mesh["positions"], mesh["triangles"]
            base_area2, centers, regions = mesh["base_area2"], mesh["centers"], mesh["regions"]
            transformed = positions.copy()
            for other_slot in [i for i in range(3) if i != slot]:
                key = (source_id, ids[other_slot])
                # The runtime currently substitutes zero for a missing flow;
                # validation intentionally reports malformed exports instead.
                if key not in flows:
                    raise ValueError(f"Missing flow {key} in pose triangle {triangle_index}")
                transformed += flows[key] * np.float32(weights[other_slot])
            vertices = transformed[triangles].astype(np.float64)
            area2 = cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
            # Keep even initially reversed/degenerate overlay triangles visible
            # in diagnostics. A negative base must not cancel a negative result.
            ratio = area2 / np.maximum(np.abs(base_area2), 1e-12)
            alpha = alpha_data[source_id]
            visible = alpha["maximum"] > VISIBLE_ALPHA
            opaque = alpha["minimum"] >= OPAQUE_ALPHA
            inverted = ratio < -INVERSION_EPSILON
            tiny_negative = (ratio < 0) & ~inverted
            weighted_area = np.maximum(-area2 * .5, 0) * weight * alpha["mean"]
            significant_area = float(weighted_area[inverted & visible].sum())
            region_rows = {}
            for region, mask in regions.items():
                roi = mask & visible
                region_rows[region] = {
                    "visible_triangles": int(roi.sum()),
                    "min_visible_area_ratio": float(ratio[roi].min()) if roi.any() else None,
                    "inverted_opaque_triangles": int((inverted & mask & opaque).sum()),
                    "inverted_alpha_edge_triangles": int((inverted & mask & visible & ~opaque).sum()),
                    "inverted_transparent_triangles": int((inverted & mask & ~visible).sum()),
                    "weighted_inverted_area_source_px2": float(weighted_area[inverted & roi].sum()),
                    "compressed_visible_triangles_ratio_below_0p1": int((roi & (ratio >= 0) & (ratio < .1)).sum()),
                    "stretched_visible_triangles_ratio_above_10": int((roi & (ratio > 10)).sum()),
                }
            witness_ids = np.flatnonzero(inverted & visible)
            worst = sorted(witness_ids, key=lambda i: ratio[i])[:3]
            witnesses = [{"mesh_triangle": int(i), "source_xy": centers[i].round(3).tolist(),
                          "rendered_xy": vertices[i].mean(axis=0).round(3).tolist(),
                          "area_ratio": float(ratio[i]),
                          "weighted_inverted_area_source_px2": float(weighted_area[i])} for i in worst]
            contributors.append({"view_id": source_id, "view": views[source_id]["name"], "weight": weight,
                                 "vertices": len(positions), "mesh_triangles": len(triangles),
                                 "nonpositive_base_triangles": int((base_area2 <= 0).sum()),
                                 "min_area_ratio_including_transparent": float(ratio.min()),
                                 "numerical_negative_triangles": int(tiny_negative.sum()),
                                 "weighted_visible_inverted_area_source_px2": significant_area,
                                 "significant_visible_failure": significant_area >= SIGNIFICANT_WEIGHTED_AREA,
                                 "regions": region_rows, "worst_visible_triangles": witnesses})
            global_witnesses.extend({"sample": sample_index, "yaw": float(pose[0]), "pitch": float(pose[1]),
                                     "view": views[source_id]["name"], "weight": weight, **witness}
                                    for witness in witnesses)
        rows.append({"kind": kind, "pose_triangle": triangle_index, "yaw": float(pose[0]), "pitch": float(pose[1]),
                     "inside_pointer_ellipse": bool(np.linalg.norm(pose / [30, 18]) <= 1 + 1e-6),
                     "contributors": contributors,
                     "significant_visible_failure": any(c["significant_visible_failure"] for c in contributors)})
        if (sample_index + 1) % 250 == 0:
            print(f"Geometry samples {sample_index + 1}/{len(samples)}", flush=True)
    failed = [row for row in rows if row["significant_visible_failure"]]
    residuals = sum(any(c["weighted_visible_inverted_area_source_px2"] > 0 for c in row["contributors"])
                    and not row["significant_visible_failure"] for row in rows)
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "FAIL" if failed else "PASS_WITH_SUBPIXEL_RESIDUALS" if residuals else "PASS",
        "scope": "CPU evaluation of actual exported GPU triangles; no browser or appearance approval",
        "field": str(field), "manifest_sha256": manifest_hash,
        "manifest_unchanged_during_check": sha(manifest_path) == manifest_hash,
        "manifest_version": manifest.get("version"), "feather_refinement": manifest.get("featherRefinement"),
        "manifest_mtime_utc": datetime.fromtimestamp(manifest_mtime, timezone.utc).isoformat(),
        "asset_sha256": asset_hashes,
        "shader_grid": representation,
        "source_meshes": [{"id": source_id, "vertices": len(mesh["positions"]),
                           "triangles": len(mesh["triangles"]),
                           "source_area_px2": float(mesh["base_area2"].sum() * .5),
                           "nonpositive_base_triangles": int((mesh["base_area2"] <= 0).sum())}
                          for source_id, mesh in meshes.items()],
        "thresholds": {"negative_area_ratio_epsilon": INVERSION_EPSILON, "visible_alpha": VISIBLE_ALPHA,
                       "opaque_alpha": OPAQUE_ALPHA, "significant_weighted_inverted_area_source_px2": SIGNIFICANT_WEIGHTED_AREA},
        "summary": {"pose_triangles": len(manifest["triangles"]), "barycentric_steps": args.steps,
                    "samples": len(rows), "significant_failure_samples": len(failed),
                    "significant_failure_samples_inside_pointer_ellipse": sum(row["inside_pointer_ellipse"] for row in failed),
                    "subpixel_residual_samples": residuals,
                    "worst_visible_area_ratio": min((w["area_ratio"] for w in global_witnesses), default=None)},
        "worst_visible_triangles": sorted(global_witnesses, key=lambda w: w["area_ratio"])[:20],
        "focused_samples": [row for row in rows if row["kind"] == "focused"],
        "samples": rows,
        "limits": ["Finite barycentric sampling does not prove all continuous poses are fold-free.",
                   "Alpha coverage uses three samples for regular cells and seven for conforming triangles; it is not an exact area integral.",
                   "Geometry passing does not certify anatomical correspondence, texture sharpness, or visual quality.",
                   "Compression/stretching is reported without a visual verdict; natural occlusion can compress surfaces."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], **report["summary"], "report": str(args.output)}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
