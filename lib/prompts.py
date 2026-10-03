#!/usr/bin/env python3
"""prompts.py — semua template prompt & naskah VO Bahasa Indonesia.

Prinsip:
  - Prompt visual ditulis dalam Bahasa Inggris (model image/video paling
    patuh pada prompt Inggris), TAPI semua teks yang muncul di video dan
    semua voice-over WAJIB Bahasa Indonesia.
  - ANOMALY_GUARD ditempel di setiap prompt visual — ini pertahanan
    lapis pertama anti tangan-berlebih/jari-aneh/produk berubah.
  - Konsistensi produk dijaga via gflow character (referensi visual),
    bukan cuma lewat kata-kata.
"""

# ---- Penjaga anti-anomali: ditempel di SETIAP prompt visual ----
ANOMALY_GUARD = (
    "Strict anatomical correctness: exactly two natural human hands, "
    "exactly five fingers per hand, no extra limbs, no extra fingers, "
    "no missing fingers, no morphing or melting, no distorted faces. "
    "The product's packaging, shape, colors, label text and branding stay "
    "pixel-identical to the reference in every frame — never redesigned, "
    "never recolored. Photorealistic, sharp focus, no on-screen text, "
    "no captions, no subtitles, no watermark, no logo added."
)

STYLE_POV = (
    "Vertical 9:16 video frame, first-person POV: ONLY hands visible, "
    "no faces, no other people. Bright clean TikTok shop aesthetic, "
    "soft daylight, shallow depth of field, attractive tidy background."
)

# ---- Tahap HD (Nano Banana 2): perjelas gambar katalog ----
def hd_prompt(product_desc: str) -> str:
    return (
        "Using Nano Banana 2, enhance this product photo to ultra HD quality. "
        f"The product is: {product_desc}. "
        "Keep the product EXACTLY the same — identical packaging, label, "
        "colors, branding, shape. Make it tack-sharp, crystal clear, "
        "professional e-commerce photography. Remove background clutter and "
        "any watermark or seller graphics that are not part of the product "
        "itself. Clean bright background. "
        + ANOMALY_GUARD
    )


# ---- Storyboard: template 3 scene generik (total 10 detik) ----
# override per produk bisa ditaruh di data/storyboards/<slug>.json
def generic_scenes(product: dict) -> list:
    name = product["name"]
    desc = product.get("product_visual", name)
    cta = product.get("cta", "cek keranjang kuning")
    return [
        {
            "n": 1, "trim": 3,
            "keyframe": (
                f"POV close-up: {desc} held by a hand next to the everyday "
                "problem it solves, on a bright clean table. Only hands visible."
            ),
            "motion": (
                "The hand brings the product toward the camera with a slight "
                "rotation showing the label. Slow subtle push-in."
            ),
            "overlay_text": "",
            "vo_line": f"Masalah ini ganggu banget? Kenalin, {name}!",
        },
        {
            "n": 2, "trim": 4,
            "keyframe": (
                f"POV close-up: hands demonstrating {desc} in use, "
                "clear visible transformation happening. Only hands visible."
            ),
            "motion": (
                "Hands use the product in a smooth satisfying demo motion; "
                "the result becomes clearly visible. Slight side angle shift."
            ),
            "overlay_text": "",
            "vo_line": "Cara pakainya gampang, hasilnya langsung kelihatan!",
        },
        {
            "n": 3, "trim": 3,
            "keyframe": (
                f"POV: hands holding {desc} front and center, bright cheerful "
                "background. Only hands visible."
            ),
            "motion": (
                "Hands lift the product slightly toward the camera. "
                "Gentle zoom-in, product stays tack-sharp."
            ),
            "overlay_text": "",
            "vo_line": f"{name}! {cta} sekarang, stok terbatas!",
        },
    ]


def scene_image_prompt(product_desc: str, scene_keyframe: str) -> str:
    return (
        "Using Nano Banana 2, create a vertical 9:16 HD storyboard frame, "
        "guided by the attached product reference. Recreate the product "
        f"EXACTLY ({product_desc}) with no changes to its packaging. "
        f"Scene: {scene_keyframe} "
        + STYLE_POV + " " + ANOMALY_GUARD
    )


# ---- Video 10 detik (Omni Flash, frames mode) ----
def video_prompt_10s(product: dict, scenes: list) -> str:
    name = product["name"]
    beats = " / ".join(
        f"[{s['trim']}s] {s['motion']}" for s in scenes
    )
    return (
        "Create a vertical 9:16 video, exactly 10 seconds, using Omni Flash, "
        "animating from the first reference frame toward the last reference "
        "frame. The product reference character must stay visually identical "
        "throughout. Story beats: " + beats + " "
        f"Product: {product.get('product_visual', name)}. "
        + STYLE_POV + " "
        "Camera: smooth realistic handheld motion, no jump cuts, no sudden "
        "scene changes. Audio: natural ambient sounds matching each beat "
        "ONLY — no spoken dialogue, no singing, no narration (voice-over is "
        "added separately). "
        + ANOMALY_GUARD
    )


# ---- Naskah voice-over Bahasa Indonesia (~10 detik ≈ 120-140 karakter) ----
def vo_script(product: dict, scenes: list) -> str:
    lines = [s["vo_line"] for s in scenes if s.get("vo_line")]
    script = " ".join(lines).strip()
    # batasi ~140 karakter biar muat 10 detik; potong di batas kata
    if len(script) > 140:
        cut = script[:140].rsplit(" ", 1)[0]
        script = cut + "!"
    return script


def build_storyboard(product: dict, override: dict | None = None) -> dict:
    """Susun storyboard.json. override = isi data/storyboards/<slug>.json."""
    if override:
        scenes_raw = override["scenes"]
        product_name = override.get("product_name", product["name"])
        product_desc = override.get("product_desc",
                                   product.get("product_visual", product_name))
    else:
        scenes_raw = generic_scenes(product)
        product_name = product["name"]
        product_desc = product.get("product_visual", product_name)

    scenes = []
    for i, sc in enumerate(scenes_raw):
        scenes.append({
            "n": i + 1,
            "trim": int(sc.get("trim", 3)),
            "keyframe": sc["keyframe"],
            "motion": sc["motion"],
            "overlay_text": sc.get("overlay_text", ""),
            "vo_line": sc.get("vo_line", ""),
            "keyframe_prompt": scene_image_prompt(product_desc, sc["keyframe"]),
        })

    total = sum(s["trim"] for s in scenes)
    return {
        "product": product_name,
        "product_desc": product_desc,
        "format": "9:16 vertical, hands-only POV, Bahasa Indonesia",
        "total_seconds": total,
        "video_prompt": video_prompt_10s(
            {"name": product_name, "product_visual": product_desc}, scenes),
        "vo_script": vo_script(
            {"name": product_name}, scenes),
        "scenes": scenes,
    }
