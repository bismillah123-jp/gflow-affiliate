#!/usr/bin/env python3
"""Generate 12 klip video ASMR deodorant via Flow agent (native video + audio)."""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = "https://flow.google.com/project/d946ec41-2494-4b55-a752-182e6067d514"
OUTDIR = ROOT / "products" / "deodorant-tawas" / "clips"
OUTDIR.mkdir(parents=True, exist_ok=True)

PROD = (
    "Product: a pink cardboard box labeled 'VANILLA' containing a natural deodorant tawas spray, "
    "and an amber brown glass spray bottle with a pink 'VANILLA' label. "
)

STYLE = (
    "Vertical 9:16 ASMR unboxing video, POV hand perspective, premium product commercial style. "
    "Photorealistic, soft natural lighting, clean aesthetic table background. "
    "NO voiceover, NO text overlay, NO watermark — only natural ASMR sounds. "
)

SCENES = [
    (1, 3, PROD + STYLE +
     "Scene: a pink 'VANILLA' product box sits on a table, hands enter the frame from both sides "
     "reaching toward the box, getting ready to unbox. Audio: soft fabric rustle as hands move."),
    (2, 3, PROD + STYLE +
     "Scene: close-up of fingers gently tapping twice on top of the pink 'VANILLA' box. "
     "Audio: light rhythmic tapping on cardboard, 'tap tap'."),
    (3, 2, PROD + STYLE +
     "Scene: hands slowly open the lid flap of the pink 'VANILLA' box, revealing the inside. "
     "Audio: soft cardboard creak as the flap opens slowly."),
    (4, 2, PROD + STYLE +
     "Scene: hands touch and lift white tissue paper inside the pink box. "
     "Audio: delicate crinkling paper sound, 'crinkle crinkle'."),
    (5, 3, PROD + STYLE +
     "Scene: hands gently move aside the tissue paper revealing the amber glass spray bottle "
     "with pink 'VANILLA' label nestled inside. Audio: soft paper crinkle."),
    (6, 2, PROD + STYLE +
     "Scene: a hand carefully lifts the amber 'VANILLA' spray bottle up out of the pink box. "
     "Audio: cardboard shift and soft glass bottle touch."),
    (7, 3, PROD + STYLE +
     "Scene: extreme close-up of the front pink 'VANILLA' label on the amber bottle, "
     "a finger gently traces across the label. Audio: soft glass slide and finger brush."),
    (8, 2, PROD + STYLE +
     "Scene: hand rotates the amber bottle to show the back label with ingredients. "
     "Audio: light fingertip tap on the glass bottle."),
    (9, 3, PROD + STYLE +
     "Scene: extreme close-up of the black spray nozzle, fingers remove the clear cap with a click. "
     "Audio: sharp plastic click sound."),
    (10, 2, PROD + STYLE +
     "Scene: slow motion close-up of fine mist spraying from the nozzle into the air, "
     "droplets sparkling in light. Audio: soft 'pssst' spray mist sound."),
    (11, 3, PROD + STYLE +
     "Scene: hand holds the full amber 'VANILLA' spray bottle upright, presenting it proudly "
     "to the camera. Audio: gentle fingertip tap on the bottle."),
    (12, 2, PROD + STYLE +
     "Scene: final beautiful shot of the amber 'VANILLA' bottle standing next to its pink box "
     "on the table, a hand waves gently out of frame. Audio: soft whoosh, calm natural ambience."),
]

def main():
    for n, dur, prompt in SCENES:
        out = OUTDIR / f"scene{n:02d}.mp4"
        if out.exists():
            print(f"scene{n:02d} sudah ada, skip")
            continue
        print(f"== scene{n:02d} ({dur}s) ==")
        cmd = [
            "node", str(ROOT / "lib" / "flow-agent.js"),
            "--project", PROJECT,
            "--prompt", prompt,
            "--out", str(out),
            "--wait", "600",
        ]
        r = subprocess.run(cmd, cwd=str(ROOT), timeout=700)
        if r.returncode != 0:
            print(f"scene{n:02d} GAGAL (exit {r.returncode}), lanjut...")
        else:
            print(f"scene{n:02d} OK")
    print("batch selesai")

if __name__ == "__main__":
    main()
