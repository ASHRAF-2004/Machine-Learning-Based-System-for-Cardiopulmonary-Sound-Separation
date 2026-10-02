"""Build the continuous two-axis StethoFuse owl pose field.

The field combines the approved neutral owl, the existing clean key poses and
the visually reviewed quarter/three-quarter anchors. Every output is solved
from its local yaw/pitch triangle; the lower body remains source-exact.
"""
from __future__ import annotations

from pathlib import Path
import argparse, hashlib, json, multiprocessing as mp, re, sys, time

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT.parents[1] / "StethoFuse-codex-package/owl-3d-lab/frame-study"
GENERATED = ROOT / "evidence/owl-continuous-atlas/generated"
OUT = ROOT / "public/assets/owl/continuous-field"
EVIDENCE = ROOT / "evidence/owl-continuous-field"
H, W, STEP = 640, 1163, 1.5
cv2.setNumThreads(1)

sys.path.insert(0, str(STUDY / "tools"))
from annotate_pose_landmarks import estimate  # noqa: E402
from compatible_mesh import compatible  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pose_angles(name: str) -> tuple[float, float]:
    if name == "neutral-original":
        return 0.0, 0.0
    match = re.fullmatch(r"yaw(?:-(minus|plus)(\d+)(?:p(\d+))?|0)-pitch(?:-(minus|plus)(\d+)(?:p(\d+))?|0)", name)
    if not match:
        raise ValueError(f"Cannot parse pose name: {name}")
    ys, yw, yf, ps, pw, pf = match.groups()
    yaw = 0.0 if yw is None else float(f"{yw}.{yf or '0'}") * (-1 if ys == "minus" else 1)
    pitch = 0.0 if pw is None else float(f"{pw}.{pf or '0'}") * (-1 if ps == "minus" else 1)
    return yaw, pitch


BASE_NAMES = [row["pose"] for row in json.loads((STUDY / "evidence/landmarks.json").read_text())["poses"]]
GENERATED_NAMES = sorted(path.stem for path in GENERATED.glob("*.json"))
SOURCES = BASE_NAMES + GENERATED_NAMES
SOURCE_PATHS = [STUDY / "assembled" / f"{name}.png" if name in BASE_NAMES else GENERATED / f"{name}.png" for name in SOURCES]
POSES = np.float32([pose_angles(name) for name in SOURCES])
IMAGES = [np.asarray(Image.open(path).convert("RGBA")) for path in SOURCE_PATHS]
NEUTRAL = IMAGES[SOURCES.index("neutral-original")]
FLOATS = []
for source_image in IMAGES:
    value = source_image[:H].astype(np.float32) / 255
    value[:, :, :3] *= value[:, :, 3:]
    FLOATS.append(value)


def correspondence_points(image: np.ndarray) -> np.ndarray:
    landmarks, debug = estimate(Image.fromarray(image))
    points: list[list[float]] = [[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]]
    for y in [60, 120, 200, 300, 410, 520, 600]:
        visible = np.where(image[y, :, 3] > 128)[0]
        points.extend([[float(max(0, visible[0] - 24)), y], [float(min(W - 1, visible[-1] + 24)), y]])
    points.extend([[490, 28], [260, 600], [430, 600], [610, 600], [790, 600], [950, 600]])
    for x0, y0, x1, y1 in debug["blue_iris_boxes_xyxy"]:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        # The iris centre is a stable correspondence. Eye-box corners are not:
        # at strong yaw the far eye becomes occluded and its corners legitimately
        # cross the beak silhouette, which inverted triangles and duplicated the
        # eye. The complete face texture still travels with the head mesh.
        points.append([cx, cy])
    base, tip = [np.float32(landmarks[key]) for key in ["beak_base", "beak_tip"]]
    axis = tip - base
    side = np.float32([axis[1], -axis[0]])
    side /= max(float(np.linalg.norm(side)), 1e-5)
    points.append(base.tolist())
    # Keep the beak as a rigid centreline-connected feature. Independent left
    # and right contour points were the other source of topology inversions.
    points.append(tip.tolist())
    return np.float32(points)


POINTS = [correspondence_points(image) for image in IMAGES]
if len({len(points) for points in POINTS}) != 1:
    raise ValueError("Pose correspondence point counts differ")


def delaunay(points: np.ndarray, bounds: tuple[int, int, int, int]) -> list[list[int]]:
    subdivision = cv2.Subdiv2D(bounds)
    for point in points:
        subdivision.insert(tuple(float(value) for value in point))
    output: list[list[int]] = []
    for triangle in subdivision.getTriangleList().reshape(-1, 3, 2):
        ids = [int(np.argmin(np.sum((points - point) ** 2, axis=1))) for point in triangle]
        if len(set(ids)) == 3 and all(np.linalg.norm(points[index] - point) < .1 for index, point in zip(ids, triangle)):
            output.append(ids)
    return output


VIEW_TRIANGLES = delaunay(POSES + np.float32([31, 19]), (0, 0, 63, 39))


def contributors(yaw: float, pitch: float) -> tuple[list[int], np.ndarray]:
    target = np.float32([yaw, pitch])
    distance = np.linalg.norm(POSES - target, axis=1)
    if distance.min() < 1e-4:
        return [int(distance.argmin())], np.float32([1])
    for ids in VIEW_TRIANGLES:
        source = POSES[ids]
        weights = np.linalg.solve(np.vstack([source.T, np.ones(3)]), np.r_[target, 1])
        if weights.min() > -1e-5:
            return ids, np.float32(np.clip(weights, 0, 1))
    raise ValueError(f"Pose outside source hull: {yaw}, {pitch}")


def render(yaw: float, pitch: float) -> tuple[np.ndarray, list[str], list[float], int]:
    ids, weights = contributors(yaw, pitch)
    if len(ids) == 1:
        return IMAGES[ids[0]][:600].copy(), [SOURCES[ids[0]]], [1.0], 0
    target = np.sum(np.asarray([POINTS[index] for index in ids]) * weights[:, None, None], axis=0).astype(np.float32)
    mesh, folds = compatible(delaunay(target, (0, 0, W, H)), target, [POINTS[index] for index in ids])
    # A disappearing far eye can invert a few tiny occluded topology cells at
    # extreme turns. Keep and report them for visual review instead of opening
    # transparent holes in the face; the visible eye/beak cells stay coherent.
    result = np.zeros((H, W, 4), np.float32)
    warped_sources: list[np.ndarray] = []
    for source_index, weight in zip(ids, weights):
        mapping = np.full((H, W, 2), -100, np.float32)
        for triangle in mesh:
            destination = target[triangle]
            x, y, width, height = cv2.boundingRect(destination)
            x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + width + 1), min(H, y + height + 1)
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            homogeneous = np.dstack([xx, yy, np.ones_like(xx)])
            mask = np.zeros(xx.shape, np.uint8)
            cv2.fillConvexPoly(mask, np.int32(np.rint(destination - [x0, y0])), 1)
            matrix = cv2.getAffineTransform(destination, POINTS[source_index][triangle])
            mapped = (homogeneous @ matrix.T).astype(np.float32)
            mapping[y0:y1, x0:x1][mask > 0] = mapped[mask > 0]
        warped = cv2.remap(FLOATS[source_index], mapping[:, :, 0], mapping[:, :, 1], cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
        warped_sources.append(warped)
        result += warped * weight
    # Interpolating photographic textures, even after geometry alignment,
    # softens tiny dark feather marks and can reveal a second far eye during an
    # occlusion change. Use the nearest clean anchor's texture on the continuous
    # interpolated geometry. This keeps every output crisp and single-featured;
    # dense 1.5° sampling makes the short source hand-offs unobtrusive.
    result = warped_sources[int(np.argmax(weights))]
    alpha = np.clip(result[:, :, 3:], 0, 1)
    rgb = result[:, :, :3] / np.maximum(alpha, 1e-5)
    rgba = np.uint8(np.clip(np.concatenate([rgb, alpha], axis=2) * 255 + .5, 0, 255))[:600]
    taper = np.clip((555 - np.arange(600)) / 42, 0, 1)[:, None, None]
    rgba = np.uint8(np.round(rgba * taper + NEUTRAL[:600] * (1 - taper)))
    rgba[555:] = NEUTRAL[555:600]
    return rgba, [SOURCES[index] for index in ids], [float(weight) for weight in weights], folds


def render_job(job: tuple[int, float, float, str, str]) -> dict:
    index, yaw, pitch, filename, mode = job
    image, sources, weights, folds = render(yaw, pitch)
    path = OUT / filename
    Image.fromarray(image).save(path, "WEBP", quality=95, method=6, exact=True)
    if mode == "validation":
        Image.fromarray(image).save(EVIDENCE / f"validation-{index:03d}.png")
    return {"index": index, "yaw": yaw, "pitch": pitch, "file": filename, "bytes": path.stat().st_size,
            "sources": sources, "weights": [round(value, 6) for value in weights], "folds": int(folds)}


def validation_positions() -> list[tuple[float, float]]:
    values: list[tuple[float, float]] = []
    for radius in [.25, .625, 1.0]:
        for angle in np.linspace(0, 2 * np.pi, 24, endpoint=False):
            values.append((30 * radius * float(np.cos(angle)), 18 * radius * float(np.sin(angle))))
    values.extend([(3.75, 2.25), (-11.25, 6.75), (18.75, -11.25), (-26.25, 15.75), (0, 0)])
    return values


def write_anchor_sheet() -> None:
    sheet = Image.new("RGB", (8 * 300, 5 * 320), "#edf5fb")
    draw = ImageDraw.Draw(sheet)
    for index, (name, image) in enumerate(zip(SOURCES, IMAGES)):
        view = Image.fromarray(image).crop((145, 0, 870, 575))
        view.thumbnail((292, 285))
        x, y = (index % 8) * 300, (index // 8) * 320
        sheet.paste(view, (x + (300 - view.width) // 2, y + 28), view)
        yaw, pitch = pose_angles(name)
        draw.text((x + 6, y + 7), f"{yaw:+g} / {pitch:+g}  {name}", fill="#22384d")
    sheet.save(EVIDENCE / "anchor-coverage.png")


def write_validation_sheet(records: list[dict]) -> None:
    sheet = Image.new("RGB", (6 * 390, 13 * 315), "#edf5fb")
    draw = ImageDraw.Draw(sheet)
    for record in records:
        image = Image.open(EVIDENCE / f"validation-{record['index']:03d}.png").convert("RGBA").crop((150, 0, 870, 555))
        image.thumbnail((380, 280))
        x, y = (record["index"] % 6) * 390, (record["index"] // 6) * 315
        sheet.paste(image, (x + 5, y + 28), image)
        draw.text((x + 7, y + 7), f"yaw {record['yaw']:+.2f}  pitch {record['pitch']:+.2f}", fill="#22384d")
    sheet.save(EVIDENCE / "circular-validation.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Build the 41×25 production grid (1025 frames)")
    parser.add_argument("--workers", type=int, default=min(4, max(1, mp.cpu_count() // 2)))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    write_anchor_sheet()
    if args.full:
        positions = [(float(x), float(y)) for y in np.arange(-18, 18.001, STEP) for x in np.arange(-30, 30.001, STEP)]
        jobs = [(index, yaw, pitch, f"pose-{round((yaw + 30) / STEP):02d}-{round((pitch + 18) / STEP):02d}.webp", "full") for index, (yaw, pitch) in enumerate(positions)]
        mode = "full"
    else:
        positions = validation_positions()
        jobs = [(index, yaw, pitch, f"validation-{index:03d}.webp", "validation") for index, (yaw, pitch) in enumerate(positions)]
        mode = "validation"
    started = time.monotonic()
    records: list[dict] = []
    with mp.get_context("fork").Pool(args.workers) as pool:
        for count, record in enumerate(pool.imap_unordered(render_job, jobs), 1):
            records.append(record)
            if count % 20 == 0 or count == len(jobs):
                print(count, len(jobs), round(time.monotonic() - started, 1), flush=True)
    records.sort(key=lambda row: row["index"])
    if mode == "validation":
        write_validation_sheet(records)
    anchors = [{"name": name, "yaw": pose_angles(name)[0], "pitch": pose_angles(name)[1], "path": str(path), "sha256": sha256(path)} for name, path in zip(SOURCES, SOURCE_PATHS)]
    manifest = {"status": "visual review required" if mode == "validation" else "production field; browser review required", "mode": mode,
                "head_dimensions": [W, 600], "grid": {"yaw_min": -30, "yaw_max": 30, "pitch_min": -18, "pitch_max": 18, "step": STEP},
                "approved_source_sha256": sha256(STUDY / "assembled/neutral-original.png"), "anchors": anchors, "frames": records,
                "build_seconds": round(time.monotonic() - started, 2), "total_bytes": sum(row["bytes"] for row in records)}
    (OUT / f"manifest-{mode}.json").write_text(json.dumps(manifest, indent=2))
    summary = {key: manifest[key] for key in ["status", "mode", "grid", "build_seconds", "total_bytes"]}
    summary.update({"anchor_count": len(anchors), "frame_count": len(records)})
    (EVIDENCE / f"build-{mode}.json").write_text(json.dumps(summary, indent=2))
    print("finished", mode, manifest["build_seconds"], "seconds", len(records), "frames")


if __name__ == "__main__":
    main()
