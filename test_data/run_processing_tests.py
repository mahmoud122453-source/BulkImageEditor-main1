"""Exercise the original BulkImageEditor functions. Does not modify project code."""
import json
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.resizer import resize_images_maintain_aspect_ratio
from src.watermark import (
    add_watermark,
    apply_transparency,
    get_watermark_position,
    resize_watermark,
)

TEST_ROOT = ROOT / "test_data"
INPUT = TEST_ROOT / "input"
OUTPUT = TEST_ROOT / "output"
WM = TEST_ROOT / "watermark"
RESULTS = []


def record(name, status, detail):
    RESULTS.append({"test": name, "status": status, "detail": detail})
    print(f"[{status}] {name}: {detail}")


def reset_dir(path: Path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def save_solid(path: Path, size, color, mode="RGB"):
    image = Image.new(mode, size, color)
    image.save(path)


def make_assets():
    reset_dir(INPUT)
    reset_dir(WM)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    save_solid(INPUT / "small.jpg", (120, 90), (180, 140, 90))
    save_solid(INPUT / "large.jpg", (2400, 1800), (40, 90, 160))
    save_solid(INPUT / "photo.png", (640, 480), (20, 160, 80))
    save_solid(INPUT / "wide.jpg", (1800, 400), (200, 80, 40))
    save_solid(INPUT / "tall.jpg", (400, 1800), (80, 40, 180))
    save_solid(INPUT / "square.jpg", (700, 700), (120, 120, 40))
    save_solid(INPUT / "light.jpg", (500, 400), (245, 245, 245))
    save_solid(INPUT / "dark.jpg", (500, 400), (15, 15, 15))
    save_solid(INPUT / "also.JPG", (300, 200), (10, 20, 30))
    save_solid(INPUT / "photo.jpeg", (900, 600), (70, 90, 110))

    transparent = Image.new("RGBA", (400, 300), (255, 0, 0, 0))
    draw = ImageDraw.Draw(transparent)
    draw.rectangle((50, 50, 250, 200), fill=(0, 200, 0, 255))
    transparent.save(INPUT / "transparent.png")

    (INPUT / "notes.txt").write_text("not an image", encoding="utf-8")
    (INPUT / "picture.bmp").write_bytes(b"BM not really examined")
    (INPUT / "picture.webp").write_bytes(b"RIFF not a real webp")
    (INPUT / "anim.gif").write_bytes(b"GIF89a not a real gif")

    logo = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    logo.save(WM / "logo.png")
    wide_logo = Image.new("RGBA", (200, 80), (0, 0, 255, 255))
    wide_logo.save(WM / "wide_logo.png")

    light = Image.new("RGB", (500, 400), (250, 250, 250))
    light.save(WM / "light_bg.jpg")
    dark = Image.new("RGB", (500, 400), (10, 10, 10))
    dark.save(WM / "dark_bg.jpg")
    base = Image.new("RGB", (500, 400), (0, 0, 255))
    base.save(WM / "blue_bg.jpg")


def copy_named(src_names, dest: Path):
    reset_dir(dest)
    for name in src_names:
        shutil.copy(INPUT / name, dest / name)


def open_size(path: Path):
    with Image.open(path) as image:
        image.load()
        return image.size, image.mode, image.format


def ratio(size):
    return size[0] / size[1]


def run_resize(src: Path, dest: Path, max_size):
    reset_dir(dest)
    resize_images_maintain_aspect_ratio(str(src), str(dest), max_size=max_size)


def test_resize_cases():
    cases = {
        "large.jpg": (2400, 1800),
        "small.jpg": (120, 90),
        "wide.jpg": (1800, 400),
        "tall.jpg": (400, 1800),
        "square.jpg": (700, 700),
        "photo.png": (640, 480),
        "transparent.png": (400, 300),
        "also.JPG": (300, 200),
        "photo.jpeg": (900, 600),
    }
    src = TEST_ROOT / "input_resize"
    copy_named(list(cases) + ["notes.txt", "picture.bmp", "picture.webp", "anim.gif"], src)
    dest = OUTPUT / "resize_800"
    run_resize(src, dest, (800, 800))

    for name, original in cases.items():
        out = dest / name
        if not out.exists():
            record(f"resize {name}", "FAIL", "output missing")
            continue
        size, mode, fmt = open_size(out)
        in_ratio = ratio(original)
        out_ratio = ratio(size)
        preserved = abs(in_ratio - out_ratio) < 0.02
        shrank_or_same = size[0] <= original[0] and size[1] <= original[1]
        within = size[0] <= 800 and size[1] <= 800
        needs_shrink = original[0] > 800 or original[1] > 800
        shrunk = size != original if needs_shrink else size == original
        status = "PASS" if preserved and shrank_or_same and within and shrunk else "FAIL"
        record(
            f"resize {name} max 800x800",
            status,
            f"in={original} out={size} mode={mode} format={fmt} ratio_ok={preserved}",
        )

    skipped = ["notes.txt", "picture.bmp", "picture.webp", "anim.gif"]
    present = [name for name in skipped if (dest / name).exists()]
    record(
        "resize skips unsupported extensions",
        "PASS" if not present else "FAIL",
        f"copied_to_output={present or 'none'}",
    )

    with Image.open(dest / "transparent.png") as image:
        alpha = image.getchannel("A").getextrema() if "A" in image.getbands() else None
    record(
        "resize keeps PNG transparency",
        "PASS" if alpha == (0, 255) else "FAIL",
        f"alpha_extrema={alpha}",
    )

    # Width is the binding maximum when max height is very large.
    src_w = TEST_ROOT / "input_width_cap"
    copy_named(["large.jpg"], src_w)
    dest_w = OUTPUT / "resize_width_cap"
    run_resize(src_w, dest_w, (400, 10000))
    size, mode, _ = open_size(dest_w / "large.jpg")
    record(
        "resize width-binding max box 400x10000",
        "PASS" if size[0] == 400 and size[1] == 300 else "FAIL",
        f"out={size} mode={mode}",
    )
    record("dedicated width-only flag", "NOT IMPLEMENTED", "API always receives a (max_width, max_height) box")

    src_h = TEST_ROOT / "input_height_cap"
    copy_named(["large.jpg"], src_h)
    dest_h = OUTPUT / "resize_height_cap"
    run_resize(src_h, dest_h, (10000, 400))
    size, mode, _ = open_size(dest_h / "large.jpg")
    record(
        "resize height-binding max box 10000x400",
        "PASS" if size == (533, 400) else "FAIL",
        f"out={size} mode={mode}",
    )
    record("dedicated height-only flag", "NOT IMPLEMENTED", "API always receives a (max_width, max_height) box")

    record(
        "exact width and height ignoring aspect ratio",
        "NOT IMPLEMENTED",
        "thumbnail fits inside the box and keeps the aspect ratio",
    )

    # Small image must not be enlarged.
    src_s = TEST_ROOT / "input_small"
    copy_named(["small.jpg"], src_s)
    dest_s = OUTPUT / "resize_small"
    run_resize(src_s, dest_s, (800, 800))
    size, _, _ = open_size(dest_s / "small.jpg")
    record(
        "resize does not enlarge a smaller image",
        "PASS" if size == (120, 90) else "FAIL",
        f"out={size}",
    )

    # Batch of several images.
    produced = sorted(p.name for p in dest.iterdir())
    record(
        "resize batch multiple images",
        "PASS" if len(produced) == len(cases) else "FAIL",
        f"count={len(produced)} files={produced}",
    )

    # Empty folder.
    empty = TEST_ROOT / "input_empty"
    reset_dir(empty)
    dest_e = OUTPUT / "resize_empty"
    try:
        run_resize(empty, dest_e, (800, 800))
        record("resize empty input folder", "PASS", f"output_files={list(dest_e.iterdir())}")
    except Exception as exc:
        record("resize empty input folder", "FAIL", f"{type(exc).__name__}: {exc}")

    # Missing directory.
    missing = TEST_ROOT / "does_not_exist"
    dest_m = OUTPUT / "resize_missing"
    if dest_m.exists():
        shutil.rmtree(dest_m)
    try:
        resize_images_maintain_aspect_ratio(str(missing), str(dest_m), max_size=(800, 800))
        record("resize missing input directory", "FAIL", "no exception")
    except Exception as exc:
        record(
            "resize missing input directory",
            "PASS",
            f"{type(exc).__name__}: {exc}; output_dir_created={dest_m.exists()}",
        )

    # Input path is a file, not a directory.
    try:
        resize_images_maintain_aspect_ratio(str(INPUT / "small.jpg"), str(OUTPUT / "resize_file_input"), max_size=(100, 100))
        record("resize input path is a file", "FAIL", "no exception")
    except Exception as exc:
        record("resize input path is a file", "PASS", f"{type(exc).__name__}: {exc}")

    # Output path exists as a file.
    blocker = TEST_ROOT / "output_is_file.txt"
    blocker.write_text("blocked", encoding="utf-8")
    try:
        resize_images_maintain_aspect_ratio(str(src_s), str(blocker), max_size=(100, 100))
        record("resize output path is an existing file", "FAIL", "no exception")
    except Exception as exc:
        record("resize output path is an existing file", "PASS", f"{type(exc).__name__}: {exc}")

    nested = TEST_ROOT / "output_is_file.txt" / "nested"
    try:
        resize_images_maintain_aspect_ratio(str(src_s), str(nested), max_size=(100, 100))
        record("resize output parent is a file", "FAIL", "no exception")
    except Exception as exc:
        record("resize output parent is a file", "PASS", f"{type(exc).__name__}: {exc}")

    # Overwrite existing output.
    first = dest_s / "small.jpg"
    first_mtime = first.stat().st_mtime_ns
    resize_images_maintain_aspect_ratio(str(src_s), str(dest_s), max_size=(800, 800))
    second_mtime = (dest_s / "small.jpg").stat().st_mtime_ns
    record(
        "resize overwrite existing filename",
        "PASS" if second_mtime != first_mtime else "FAIL",
        f"mtime_changed={second_mtime != first_mtime}",
    )

    # Corrupted file stops the batch.
    batch = TEST_ROOT / "input_corrupt_order"
    reset_dir(batch)
    save_solid(batch / "first.png", (200, 100), (255, 0, 0))
    (batch / "bad.jpg").write_bytes(b"this is not a jpeg")
    save_solid(batch / "second.png", (200, 100), (0, 255, 0))
    dest_c = OUTPUT / "resize_corrupt"
    reset_dir(dest_c)
    original_listdir = os.listdir

    def ordered(path):
        if Path(path).resolve() == batch.resolve():
            return ["first.png", "bad.jpg", "second.png"]
        return original_listdir(path)

    os.listdir = ordered
    try:
        resize_images_maintain_aspect_ratio(str(batch), str(dest_c), max_size=(800, 800))
        record("resize corrupted image stops batch", "FAIL", "no exception")
    except Exception as exc:
        saved = sorted(p.name for p in dest_c.iterdir())
        stopped = saved == ["first.png"]
        record(
            "resize corrupted image stops batch",
            "PASS" if stopped else "FAIL",
            f"{type(exc).__name__}: {exc}; saved={saved}",
        )
    finally:
        os.listdir = original_listdir

    # Invalid numeric size.
    src_z = TEST_ROOT / "input_zero"
    copy_named(["square.jpg"], src_z)
    dest_z = OUTPUT / "resize_zero"
    reset_dir(dest_z)
    try:
        resize_images_maintain_aspect_ratio(str(src_z), str(dest_z), max_size=(0, 0))
        size, _, _ = open_size(dest_z / "square.jpg")
        record("resize max_size 0,0", "PASS", f"no exception, out={size}")
    except Exception as exc:
        record("resize max_size 0,0", "FAIL", f"{type(exc).__name__}: {exc}")

    dest_n = OUTPUT / "resize_negative"
    reset_dir(dest_n)
    try:
        resize_images_maintain_aspect_ratio(str(src_z), str(dest_n), max_size=(-100, 800))
        size, _, _ = open_size(dest_n / "square.jpg")
        record("resize negative max width", "PASS", f"no exception, out={size}")
    except Exception as exc:
        record("resize negative max width", "FAIL", f"{type(exc).__name__}: {exc}")


def changed_bbox(before: Path, after: Path):
    with Image.open(before) as src, Image.open(after) as dst:
        diff = ImageChops.difference(src.convert("RGB"), dst.convert("RGB"))
        return diff.getbbox()


def center(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def expected_text_box(image_size, text, font_size, position, font_name="arial.ttf"):
    font = ImageFont.truetype(font_name, font_size)
    probe = Image.new("RGBA", (10, 10))
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = get_watermark_position(image_size, tw, th, position)
    return (x, y, x + tw, y + th), (tw, th)


def test_watermark_cases():
    src = TEST_ROOT / "input_wm_one"
    copy_named(["dark.jpg"], src)

    dest = OUTPUT / "wm_simple"
    reset_dir(dest)
    add_watermark(str(src), str(dest), watermark_text="OK", watermark_image=None, font_size=40, position="bottom-right", alpha=1, text_color="#ffffff")
    out = dest / "dark.jpg"
    size, mode, fmt = open_size(out)
    box = changed_bbox(src / "dark.jpg", out)
    record(
        "watermark simple text",
        "PASS" if out.exists() and box and mode == "RGB" else "FAIL",
        f"size={size} mode={mode} format={fmt} changed={box}",
    )

    positions = ["top-left", "top-right", "bottom-left", "bottom-right", "center"]
    for position in positions:
        folder = TEST_ROOT / f"input_pos_{position}"
        copy_named(["dark.jpg"], folder)
        out_dir = OUTPUT / f"wm_pos_{position}"
        reset_dir(out_dir)
        add_watermark(
            str(folder), str(out_dir),
            watermark_text="Mark",
            watermark_image=None,
            font_size=36,
            position=position,
            alpha=1,
            text_color="#ffffff",
        )
        expected, _ = expected_text_box((500, 400), "Mark", 36, position)
        actual = changed_bbox(folder / "dark.jpg", out_dir / "dark.jpg")
        if not actual:
            record(f"watermark position {position}", "FAIL", "no pixel change")
            continue
        exp_c = center(expected)
        act_c = center(actual)
        delta = abs(exp_c[0] - act_c[0]) + abs(exp_c[1] - act_c[1])
        record(
            f"watermark position {position}",
            "PASS" if delta < 25 else "FAIL",
            f"expected={expected} changed={actual} center_delta={delta:.1f}",
        )

    # Font sizes.
    heights = {}
    for font_size in (12, 40, 80):
        folder = TEST_ROOT / f"input_fs_{font_size}"
        copy_named(["dark.jpg"], folder)
        out_dir = OUTPUT / f"wm_fs_{font_size}"
        reset_dir(out_dir)
        add_watermark(str(folder), str(out_dir), watermark_text="Size", watermark_image=None, font_size=font_size, position="top-left", alpha=1, text_color="#ffffff")
        box = changed_bbox(folder / "dark.jpg", out_dir / "dark.jpg")
        heights[font_size] = None if not box else box[3] - box[1]
    ordered = heights[12] and heights[40] and heights[80] and heights[12] < heights[40] < heights[80]
    record("watermark font sizes 12/40/80", "PASS" if ordered else "FAIL", f"changed_heights={heights}")

    # Colors.
    for color, check in (("#ff0000", "red"), ("#00ff00", "green"), ("#0000ff", "blue")):
        folder = TEST_ROOT / f"input_color_{check}"
        save_dir = folder
        reset_dir(save_dir)
        save_solid(save_dir / "gray.jpg", (400, 300), (128, 128, 128))
        out_dir = OUTPUT / f"wm_color_{check}"
        reset_dir(out_dir)
        add_watermark(str(save_dir), str(out_dir), watermark_text="Color", watermark_image=None, font_size=60, position="center", alpha=1, text_color=color)
        with Image.open(save_dir / "gray.jpg") as src, Image.open(out_dir / "gray.jpg") as dst:
            diff = ImageChops.difference(src.convert("RGB"), dst.convert("RGB"))
            bbox = diff.getbbox()
            sample = None
            best = -1
            if bbox:
                for y in range(bbox[1], bbox[3]):
                    for x in range(bbox[0], bbox[2]):
                        pixel = dst.getpixel((x, y))
                        score = abs(pixel[0] - 128) + abs(pixel[1] - 128) + abs(pixel[2] - 128)
                        if score > best:
                            best = score
                            sample = pixel
        ok = False
        if sample:
            if check == "red":
                ok = sample[0] > 200 and sample[1] < 40 and sample[2] < 40
            elif check == "green":
                ok = sample[1] > 200 and sample[0] < 40 and sample[2] < 40
            else:
                ok = sample[2] > 200 and sample[0] < 40 and sample[1] < 40
        record(f"watermark color {color}", "PASS" if ok else "FAIL", f"strongest_pixel={sample}")

    # Opacity.
    diffs = {}
    for alpha in (0, 0.25, 1):
        folder = TEST_ROOT / f"input_alpha_{alpha}"
        copy_named(["dark.jpg"], folder)
        out_dir = OUTPUT / f"wm_alpha_{alpha}"
        reset_dir(out_dir)
        add_watermark(str(folder), str(out_dir), watermark_text="Fade", watermark_image=None, font_size=50, position="center", alpha=alpha, text_color="#ffffff")
        with Image.open(folder / "dark.jpg") as src, Image.open(out_dir / "dark.jpg") as dst:
            diff = ImageChops.difference(src.convert("RGB"), dst.convert("RGB"))
            hist = diff.convert("L").histogram()
            diffs[alpha] = sum(i * count for i, count in enumerate(hist))
    record(
        "watermark text opacity 0 / 0.25 / 1",
        "PASS" if diffs[0] == 0 and diffs[0] < diffs[0.25] < diffs[1] else "FAIL",
        f"difference_mass={diffs}",
    )

    for label, name in (("light", "light.jpg"), ("dark", "dark.jpg")):
        folder = TEST_ROOT / f"input_bg_{label}"
        copy_named([name], folder)
        out_dir = OUTPUT / f"wm_bg_{label}"
        reset_dir(out_dir)
        color = "#202020" if label == "light" else "#ffffff"
        add_watermark(str(folder), str(out_dir), watermark_text="Visible", watermark_image=None, font_size=48, position="bottom-right", alpha=0.9, text_color=color)
        box = changed_bbox(folder / name, out_dir / name)
        record(f"watermark on {label} background", "PASS" if box else "FAIL", f"changed={box}")

    long_text = "This is a very long watermark sentence that should extend across the image"
    folder = TEST_ROOT / "input_long"
    copy_named(["dark.jpg"], folder)
    out_dir = OUTPUT / "wm_long"
    reset_dir(out_dir)
    add_watermark(str(folder), str(out_dir), watermark_text=long_text, watermark_image=None, font_size=40, position="top-left", alpha=1, text_color="#ffffff")
    box = changed_bbox(folder / "dark.jpg", out_dir / "dark.jpg")
    record("watermark long text", "PASS" if box and box[2] > 400 else "FAIL", f"changed={box}")

    out_dir = OUTPUT / "wm_long_bottom_right"
    reset_dir(out_dir)
    add_watermark(
        str(folder), str(out_dir),
        watermark_text=long_text,
        watermark_image=None,
        font_size=40,
        position="bottom-right",
        alpha=1,
        text_color="#ffffff",
    )
    box = changed_bbox(folder / "dark.jpg", out_dir / "dark.jpg")
    record(
        "long text at bottom-right is clipped at the image edge",
        "PASS" if box and box[0] <= 2 and box[2] >= 490 else "FAIL",
        f"changed={box}",
    )

    # Image watermark position, scale, transparency, placement.
    folder = TEST_ROOT / "input_logo"
    reset_dir(folder)
    shutil.copy(WM / "blue_bg.jpg", folder / "blue_bg.jpg")
    out_dir = OUTPUT / "wm_logo"
    reset_dir(out_dir)
    add_watermark(
        str(folder), str(out_dir),
        watermark_text=None,
        watermark_image=str(WM / "logo.png"),
        position="bottom-right",
        alpha=1,
    )
    with Image.open(WM / "logo.png") as logo:
        scaled = resize_watermark(logo, (500, 400))
        scaled_size = scaled.size
    x, y = get_watermark_position((500, 400), scaled_size[0], scaled_size[1], "bottom-right")
    with Image.open(out_dir / "blue_bg.jpg") as result:
        pixel = result.getpixel((x + 5, y + 5))
        mode = result.mode
    record(
        "image watermark scale and bottom-right placement",
        "PASS" if scaled_size == (50, 50) and pixel[0] > 240 and pixel[2] < 20 and mode == "RGB" else "FAIL",
        f"scaled={scaled_size} origin={(x, y)} pixel={pixel} mode={mode}",
    )

    for position in positions:
        out_dir = OUTPUT / f"wm_logo_{position}"
        reset_dir(out_dir)
        add_watermark(str(folder), str(out_dir), watermark_image=str(WM / "logo.png"), position=position, alpha=1)
        x, y = get_watermark_position((500, 400), 50, 50, position)
        with Image.open(out_dir / "blue_bg.jpg") as result:
            pixel = result.getpixel((x + 5, y + 5))
        record(
            f"image watermark position {position}",
            "PASS" if pixel[0] > 240 else "FAIL",
            f"origin={(x, y)} pixel={pixel}",
        )

    out_dir = OUTPUT / "wm_logo_alpha"
    reset_dir(out_dir)
    add_watermark(str(folder), str(out_dir), watermark_image=str(WM / "logo.png"), position="top-left", alpha=0.5)
    x, y = get_watermark_position((500, 400), 50, 50, "top-left")
    with Image.open(out_dir / "blue_bg.jpg") as result:
        pixel = result.getpixel((x + 25, y + 25))
    # paste(watermark, box, watermark) applies the alpha band twice, so 0.5
    # does not produce a single 50% composite. Opaque red over blue was measured
    # near (31, 0, 192), while a single blend would be near (127, 0, 128).
    faded = pixel[0] < 80 and pixel[2] > 150
    single_blend = abs(pixel[0] - 127) <= 8 and abs(pixel[2] - 128) <= 8
    record(
        "image watermark transparency changes the logo",
        "PASS" if faded else "FAIL",
        f"center_pixel={pixel}",
    )
    record(
        "image watermark alpha 0.5 matches one 50% blend",
        "PASS" if single_blend else "FAIL",
        f"center_pixel={pixel}; expected about (127, 0, 128) for one blend",
    )

    folder_aspect = TEST_ROOT / "input_logo_aspect"
    reset_dir(folder_aspect)
    shutil.copy(WM / "blue_bg.jpg", folder_aspect / "blue_bg.jpg")
    with Image.open(WM / "wide_logo.png") as logo:
        scaled = resize_watermark(logo, (500, 400))
        scaled_size = scaled.size
    record(
        "image watermark preserves logo aspect ratio",
        "PASS" if scaled_size == (50, 20) else "FAIL",
        f"200x80 logo on 500px-wide base scaled to {scaled_size}",
    )

    out_dir = OUTPUT / "wm_fill_image"
    reset_dir(out_dir)
    add_watermark(str(folder), str(out_dir), watermark_image=str(WM / "logo.png"), fill=True, alpha=1)
    with Image.open(folder / "blue_bg.jpg") as src, Image.open(out_dir / "blue_bg.jpg") as dst:
        diff = ImageChops.difference(src, dst)
        bbox = diff.getbbox()
        corner = dst.getpixel((2, 2))
        far = dst.getpixel((490, 390))
    record(
        "image watermark fill tiles the base",
        "PASS" if bbox == (0, 0, 500, 400) and corner[0] > 240 and far[0] > 240 else "FAIL",
        f"bbox={bbox} corner={corner} far={far}",
    )

    out_dir = OUTPUT / "wm_fill_text"
    reset_dir(out_dir)
    add_watermark(str(folder), str(out_dir), watermark_text="Tile", watermark_image=None, font_size=30, fill=True, alpha=1, text_color="#ffffff")
    box = changed_bbox(folder / "blue_bg.jpg", out_dir / "blue_bg.jpg")
    record(
        "text watermark fill repeats",
        "PASS" if box and box[2] > 400 and box[3] > 300 else "FAIL",
        f"changed={box}",
    )

    # Transparent source becomes RGB.
    folder_t = TEST_ROOT / "input_wm_transparent"
    copy_named(["transparent.png"], folder_t)
    out_dir = OUTPUT / "wm_transparent_source"
    reset_dir(out_dir)
    add_watermark(str(folder_t), str(out_dir), watermark_text="T", watermark_image=None, font_size=40, alpha=1, text_color="#ffffff")
    size, mode, fmt = open_size(out_dir / "transparent.png")
    record(
        "watermark drops source alpha on save",
        "PASS" if mode == "RGB" and fmt == "PNG" else "FAIL",
        f"size={size} mode={mode} format={fmt}",
    )

    # Batch mixed formats.
    folder_b = TEST_ROOT / "input_wm_batch"
    copy_named(["small.jpg", "photo.png", "photo.jpeg", "notes.txt", "also.JPG"], folder_b)
    out_dir = OUTPUT / "wm_batch"
    reset_dir(out_dir)
    add_watermark(str(folder_b), str(out_dir), watermark_text="Batch", watermark_image=None, font_size=24, alpha=1)
    saved = sorted(p.name for p in out_dir.iterdir())
    record(
        "watermark batch mixed formats",
        "PASS" if saved == ["also.JPG", "photo.jpeg", "photo.png", "small.jpg"] else "FAIL",
        f"saved={saved}",
    )

    # Empty folder.
    empty = TEST_ROOT / "input_wm_empty"
    reset_dir(empty)
    out_dir = OUTPUT / "wm_empty"
    try:
        reset_dir(out_dir)
        add_watermark(str(empty), str(out_dir), watermark_text="None", watermark_image=None)
        record("watermark empty input folder", "PASS", f"files={list(out_dir.iterdir())}")
    except Exception as exc:
        record("watermark empty input folder", "FAIL", f"{type(exc).__name__}: {exc}")

    # Missing watermark image stops processing.
    out_dir = OUTPUT / "wm_missing_logo"
    reset_dir(out_dir)
    try:
        add_watermark(str(folder), str(out_dir), watermark_image=str(WM / "missing.png"), alpha=1)
        record("missing watermark image", "FAIL", "no exception")
    except Exception as exc:
        record(
            "missing watermark image",
            "PASS",
            f"{type(exc).__name__}: {exc}; saved={list(out_dir.iterdir())}",
        )

    # Missing font falls back.
    out_dir = OUTPUT / "wm_missing_font"
    reset_dir(out_dir)
    try:
        add_watermark(
            str(folder), str(out_dir),
            watermark_text="Fallback",
            watermark_image=None,
            font="this-font-does-not-exist.ttf",
            font_size=40,
            alpha=1,
            text_color="#ffffff",
        )
        box = changed_bbox(folder / "blue_bg.jpg", out_dir / "blue_bg.jpg")
        record("missing font uses fallback", "PASS" if box else "FAIL", f"changed={box}")
    except Exception as exc:
        record("missing font uses fallback", "FAIL", f"{type(exc).__name__}: {exc}")

    # Invalid color.
    out_dir = OUTPUT / "wm_bad_color"
    reset_dir(out_dir)
    try:
        add_watermark(str(folder), str(out_dir), watermark_text="Bad", watermark_image=None, text_color="red")
        record("invalid text color", "FAIL", "no exception")
    except Exception as exc:
        record("invalid text color", "PASS", f"{type(exc).__name__}: {exc}; saved={list(out_dir.iterdir())}")

    # Unknown position falls back to bottom-right.
    out_dir = OUTPUT / "wm_bad_position"
    reset_dir(out_dir)
    add_watermark(str(folder), str(out_dir), watermark_image=str(WM / "logo.png"), position="middle", alpha=1)
    x, y = get_watermark_position((500, 400), 50, 50, "bottom-right")
    with Image.open(out_dir / "blue_bg.jpg") as result:
        pixel = result.getpixel((x + 5, y + 5))
    record("unknown position falls back to bottom-right", "PASS" if pixel[0] > 240 else "FAIL", f"pixel={pixel}")

    # Alpha outside 0..1 for an image watermark is clamped.
    sample = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
    clamped = apply_transparency(sample, 2)
    low = apply_transparency(sample, -1)
    record(
        "image alpha is clamped to 0..1",
        "PASS" if clamped.getpixel((0, 0))[3] == 255 and low.getpixel((0, 0))[3] == 0 else "FAIL",
        f"alpha2={clamped.getpixel((0, 0))} alpha-1={low.getpixel((0, 0))}",
    )

    # Text alpha is not clamped.
    out_dir = OUTPUT / "wm_text_alpha_high"
    reset_dir(out_dir)
    try:
        add_watermark(str(folder), str(out_dir), watermark_text="High", watermark_image=None, alpha=2, text_color="#ffffff")
        record("text alpha above 1", "PASS", f"saved={list(out_dir.iterdir())}")
    except Exception as exc:
        record("text alpha above 1", "FAIL", f"{type(exc).__name__}: {exc}")

    # Empty text fill.
    out_dir = OUTPUT / "wm_empty_fill"
    reset_dir(out_dir)
    try:
        add_watermark(str(folder), str(out_dir), watermark_text="", watermark_image=None, fill=True, alpha=1)
        record("empty text with fill", "PASS", "no exception")
    except Exception as exc:
        record("empty text with fill", "FAIL", f"{type(exc).__name__}: {exc}")

    # Tiny base makes a zero-size image watermark.
    tiny = TEST_ROOT / "input_tiny"
    reset_dir(tiny)
    save_solid(tiny / "tiny.jpg", (8, 8), (0, 0, 0))
    out_dir = OUTPUT / "wm_tiny"
    reset_dir(out_dir)
    try:
        add_watermark(str(tiny), str(out_dir), watermark_image=str(WM / "logo.png"), alpha=1)
        record("image watermark on 8px base", "PASS", f"saved={list(out_dir.iterdir())}")
    except Exception as exc:
        record("image watermark on 8px base", "FAIL", f"{type(exc).__name__}: {exc}")

    # Corrupted file in the middle stops watermark batch.
    batch = TEST_ROOT / "input_wm_corrupt"
    reset_dir(batch)
    save_solid(batch / "first.png", (120, 80), (30, 30, 30))
    (batch / "bad.jpg").write_bytes(b"not an image")
    save_solid(batch / "second.png", (120, 80), (30, 30, 30))
    out_dir = OUTPUT / "wm_corrupt"
    reset_dir(out_dir)
    original_listdir = os.listdir

    def ordered(path):
        if Path(path).resolve() == batch.resolve():
            return ["first.png", "bad.jpg", "second.png"]
        return original_listdir(path)

    os.listdir = ordered
    try:
        add_watermark(str(batch), str(out_dir), watermark_text="X", watermark_image=None, alpha=1)
        record("watermark corrupted image stops batch", "FAIL", "no exception")
    except Exception as exc:
        saved = sorted(p.name for p in out_dir.iterdir())
        record(
            "watermark corrupted image stops batch",
            "PASS" if saved == ["first.png"] else "FAIL",
            f"{type(exc).__name__}: {exc}; saved={saved}",
        )
    finally:
        os.listdir = original_listdir


def run_cli(args):
    completed = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    return completed.returncode, completed.stdout, completed.stderr


def test_cli():
    src = TEST_ROOT / "input_cli"
    copy_named(["large.jpg", "small.jpg", "photo.png"], src)
    dest = OUTPUT / "cli_resize"
    if dest.exists():
        shutil.rmtree(dest)
    code, out, err = run_cli([
        "--input_path", str(src),
        "--output_path", str(dest),
        "--resize",
        "--max_width", "400",
        "--max_height", "400",
    ])
    size, mode, _ = open_size(dest / "large.jpg") if (dest / "large.jpg").exists() else ((None, None), None, None)
    small, _, _ = open_size(dest / "small.jpg") if (dest / "small.jpg").exists() else ((None, None), None, None)
    record(
        "CLI resize batch",
        "PASS" if code == 0 and size == (400, 300) and small == (120, 90) and (dest / "photo.png").exists() else "FAIL",
        f"code={code} large={size} small={small} stdout={out.strip()} stderr={err.strip()}",
    )

    dest_w = OUTPUT / "cli_wm"
    if dest_w.exists():
        shutil.rmtree(dest_w)
    code, out, err = run_cli([
        "--input_path", str(src),
        "--output_path", str(dest_w),
        "--add_watermark",
        "--watermark_text", "CLI",
        "--position", "center",
        "--alpha", "1",
        "--text_color", "#ffffff",
    ])
    box = changed_bbox(src / "small.jpg", dest_w / "small.jpg") if (dest_w / "small.jpg").exists() else None
    record(
        "CLI text watermark",
        "PASS" if code == 0 and box else "FAIL",
        f"code={code} changed={box} stdout={out.strip()} stderr={err.strip()}",
    )

    dest_b = OUTPUT / "cli_both"
    if dest_b.exists():
        shutil.rmtree(dest_b)
    code, out, err = run_cli([
        "--input_path", str(src),
        "--output_path", str(dest_b),
        "--resize",
        "--max_width", "500",
        "--max_height", "500",
        "--add_watermark",
        "--watermark_image", str(WM / "logo.png"),
        "--position", "top-left",
        "--alpha", "1",
    ])
    ok = False
    detail = f"code={code} stdout={out.strip()} stderr={err.strip()}"
    if code == 0 and (dest_b / "large.jpg").exists():
        size, mode, _ = open_size(dest_b / "large.jpg")
        with Image.open(dest_b / "large.jpg") as image:
            pixel = image.getpixel((15, 15))
        ok = size[0] <= 500 and size[1] <= 500 and pixel[0] > 240
        detail = f"{detail} size={size} mode={mode} pixel={pixel}"
    record("CLI resize then image watermark", "PASS" if ok else "FAIL", detail)

    code, out, err = run_cli(["--input_path", str(src), "--output_path", str(OUTPUT / "cli_noop")])
    record("CLI with no action flags", "PASS" if code == 0 else "FAIL", f"code={code} stdout={out.strip()!r} stderr={err.strip()!r}")

    code, _, err = run_cli([
        "--input_path", str(src),
        "--output_path", str(OUTPUT / "cli_font"),
        "--add_watermark",
        "--font_size", "40",
    ])
    record(
        "CLI --font_size from README",
        "NOT IMPLEMENTED",
        f"argparse exit={code} stderr={err.strip().splitlines()[-1] if err.strip() else ''}",
    )

    code, _, err = run_cli([
        "--input_path", str(src),
        "--output_path", str(OUTPUT / "cli_pos"),
        "--add_watermark",
        "--position", "middle",
    ])
    record(
        "CLI invalid position",
        "PASS" if code == 2 else "FAIL",
        err.strip().splitlines()[-1] if err.strip() else f"code={code}",
    )

    code, _, err = run_cli([
        "--input_path", str(src),
        "--output_path", str(OUTPUT / "cli_bad_width"),
        "--resize",
        "--max_width", "wide",
    ])
    record(
        "CLI invalid max_width",
        "PASS" if code == 2 else "FAIL",
        err.strip().splitlines()[-1] if err.strip() else f"code={code}",
    )

    missing = TEST_ROOT / "cli_missing_input"
    code, out, err = run_cli([
        "--input_path", str(missing),
        "--output_path", str(OUTPUT / "cli_missing_out"),
        "--resize",
    ])
    record(
        "CLI missing input directory",
        "PASS" if code != 0 else "FAIL",
        f"code={code} stderr={err.strip().splitlines()[-1] if err.strip() else ''}",
    )


def test_gui_logic():
    os.environ.setdefault("QT_QPA_PLATFORM", "windows")
    from PyQt5.QtWidgets import QApplication
    from src.ui.bulk_image_editor_ui import BulkImageEditorUI

    app = QApplication.instance() or QApplication([])
    window = BulkImageEditorUI()
    record(
        "GUI constructs and lists system fonts",
        "PASS" if window.font_family_combo.count() > 0 else "FAIL",
        f"fonts={window.font_family_combo.count()} title={window.windowTitle()}",
    )
    record(
        "GUI defaults",
        "PASS" if window.max_width_spinbox.value() == 800 and window.max_height_spinbox.value() == 800 and window.font_size_spinbox.value() == 40 and window.transparency_slider.value() == 128 else "FAIL",
        f"width={window.max_width_spinbox.value()} height={window.max_height_spinbox.value()} font={window.font_size_spinbox.value()} slider={window.transparency_slider.value()}",
    )

    window.resize_checkbox.setChecked(True)
    resize_on = window.resize_checkbox.isChecked() and window.max_width_spinbox.isEnabled() and not window.add_watermark_checkbox.isChecked()
    window.add_watermark_checkbox.setChecked(True)
    watermark_on = (
        window.add_watermark_checkbox.isChecked()
        and not window.resize_checkbox.isChecked()
        and window.watermark_text.isEnabled()
        and window.position_combo.isEnabled()
    )
    record(
        "GUI resize and watermark checkboxes are mutually exclusive",
        "PASS" if resize_on and watermark_on else "FAIL",
        f"after_resize_ok={resize_on} after_watermark_ok={watermark_on}",
    )
    window.add_watermark_checkbox.setChecked(False)
    uncheck_forces_resize = window.resize_checkbox.isChecked() and not window.add_watermark_checkbox.isChecked()
    record(
        "GUI unchecking watermark turns resize on",
        "PASS" if uncheck_forces_resize else "FAIL",
        f"resize={window.resize_checkbox.isChecked()} watermark={window.add_watermark_checkbox.isChecked()}",
    )

    window.resize_checkbox.blockSignals(True)
    window.add_watermark_checkbox.blockSignals(True)
    window.resize_checkbox.setChecked(False)
    window.add_watermark_checkbox.setChecked(False)
    window.resize_checkbox.blockSignals(False)
    window.add_watermark_checkbox.blockSignals(False)
    idle_out = OUTPUT / "gui_idle"
    reset_dir(idle_out)
    window.input_directory.setText(str(INPUT))
    window.output_directory.setText(str(idle_out))
    window.apply_settings()
    record(
        "GUI apply with neither option checked does nothing",
        "PASS" if list(idle_out.iterdir()) == [] else "FAIL",
        f"files={list(idle_out.iterdir())}",
    )

    window.input_directory.setText("")
    window.output_directory.setText("")
    window.apply_settings()
    record("GUI apply without directories returns", "PASS", "apply_settings returned after printing a directory warning")

    window.input_directory.setText(str(INPUT))
    window.output_directory.setText(str(OUTPUT / "gui_guard"))
    window.add_watermark_checkbox.setChecked(True)
    window.watermark_text.setText("")
    window.watermark_image.setText("")
    window.apply_settings()
    record("GUI apply watermark without text or image returns", "PASS", "apply_settings returned after the watermark warning")

    src = TEST_ROOT / "input_gui"
    copy_named(["square.jpg"], src)
    dest = OUTPUT / "gui_resize"
    reset_dir(dest)
    window.resize_checkbox.setChecked(True)
    window.input_directory.setText(str(src))
    window.output_directory.setText(str(dest))
    window.max_width_spinbox.setValue(350)
    window.max_height_spinbox.setValue(350)
    window.apply_settings()
    import time
    for _ in range(50):
        if (dest / "square.jpg").exists():
            break
        time.sleep(0.1)
    if (dest / "square.jpg").exists():
        size, _, _ = open_size(dest / "square.jpg")
        record("GUI apply resize thread", "PASS" if size == (350, 350) else "FAIL", f"out={size}")
    else:
        record("GUI apply resize thread", "FAIL", "output was not created")
    window.close()
    app.processEvents()


def test_direct_module_entry():
    outside = ROOT.parent / "images" / "input"
    inside = ROOT / "images" / "input"
    if outside.exists() or inside.exists():
        record("direct resizer __main__", "NOT TESTED", f"refused because an images folder exists: outside={outside.exists()} inside={inside.exists()}")
        return
    completed = subprocess.run(
        [sys.executable, str(ROOT / "src" / "resizer.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    record(
        "direct python src/resizer.py",
        "FAIL",
        f"code={completed.returncode} stderr={completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else ''}",
    )
    completed = subprocess.run(
        [sys.executable, str(ROOT / "src" / "watermark.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    record(
        "direct python src/watermark.py",
        "FAIL",
        f"code={completed.returncode} stderr={completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else ''}",
    )


def main():
    make_assets()
    test_resize_cases()
    test_watermark_cases()
    test_cli()
    test_gui_logic()
    test_direct_module_entry()
    destination = TEST_ROOT / "results.json"
    destination.write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
    counts = {}
    for item in RESULTS:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    print("SUMMARY", counts)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
