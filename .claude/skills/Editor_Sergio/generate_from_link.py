#!/usr/bin/env python3
"""
viral-pipeline — 1 link → adaptaciones → vídeos (salida 100% LOCAL).

Esta versión NO usa Airtable en el flujo. Cada vídeo se guarda en
~/Desktop/viral_pipeline_output/<Avatar>/<slug-del-hook>/.

El agent orquesta POR FASES con gates (el usuario aprueba en cada una):
  Fase A  phase_a_audio   → TTS + post  → GATE (escuchar antes de gastar HeyGen)
  Fase B  phase_b_heygen  → avatar HeyGen → GATE (validar lip-sync/look)
  Fase C  phase_c_edit    → B-roll + subs + música → vídeo final local

(Las funciones airtable_* siguen DORMIDAS en pipeline_core por si en el futuro
se re-conecta un backend, pero no se invocan aquí.)
"""
from __future__ import annotations
import traceback
from pathlib import Path

from pipeline_core import (
    load_env, WORK_DIR,
    download_reel, transcribe_video,
    tts_elevenlabs, process_audio,
    heygen_generate_for_env, heygen_wait_for_env, burn_subs_and_music,
    save_local, slugify, bump_success_counter, audio_params_for_env,
    get_ffmpeg_exe, _get_duration,
)


# ============================================================
# STEP 1 — download + transcribe (1 vez por link)
# ============================================================
def step1_download_and_transcribe(link: str) -> dict:
    work = WORK_DIR / "single_link"
    work.mkdir(parents=True, exist_ok=True)
    print(f"[1/2] descargando {link}...")
    mp4 = download_reel(link, work)
    print("[2/2] transcribiendo...")
    text, lang = transcribe_video(mp4)
    return {
        "link": link,
        "transcript": text,
        "lang": lang,
        "duration_estimate_seconds": int(len(text.split()) * 0.4),
        "local_path": str(mp4),
    }


# ============================================================
# FASE A — audio (TTS + post). GATE antes de gastar HeyGen.
# ============================================================
def phase_a_audio(env: dict, script: str, avatar: str, slug: str) -> dict:
    workdir = WORK_DIR / f"{avatar}_{slug}"
    workdir.mkdir(parents=True, exist_ok=True)
    print("  [TTS] ElevenLabs eleven_v3...")
    raw = tts_elevenlabs(script, env["ELEVENLABS_VOICE_ID"],
                         env["ELEVENLABS_API_KEY"], workdir / "tts_raw.mp3")
    # Deriva del estilo en runtime (NO del TTS_TEMPO congelado en env)
    tempo, aggro = audio_params_for_env(env)
    print(f"  [audio] atempo={tempo} silence_aggressive={aggro} (estilo={env.get('AUDIO_STYLE','reel')})...")
    final = process_audio(raw, workdir / "audio_final.mp3",
                          tempo=tempo, silence_aggressive=aggro)
    ff = get_ffmpeg_exe()
    local = save_local(avatar, slug, "Audio", final)
    return {"ok": True, "audio_path": str(final), "local_path": str(local),
            "raw_seconds": round(_get_duration(raw, ff), 1),
            "final_seconds": round(_get_duration(final, ff), 1)}


# ============================================================
# FASE B — HeyGen (avatar V o IV según env). GATE antes de editar.
# ============================================================
def phase_b_heygen(env: dict, audio_path: str, avatar: str, slug: str) -> dict:
    workdir = WORK_DIR / f"{avatar}_{slug}"
    workdir.mkdir(parents=True, exist_ok=True)
    engine = (env.get("HEYGEN_ENGINE") or "avatar_iv")
    print(f"  [HeyGen] generando ({engine})...")
    try:
        vid = heygen_generate_for_env(Path(audio_path), env)
        if not vid:
            raise RuntimeError(
                "HeyGen no devolvió video_id (revisar look_id/engine/key)")
        heygen_mp4 = workdir / "heygen.mp4"
        ok = heygen_wait_for_env(vid, env, heygen_mp4)
        if not ok:
            raise RuntimeError(f"HeyGen failed para video_id {vid}")
        local = save_local(avatar, slug, "Video Heygen", heygen_mp4)
        ff = get_ffmpeg_exe()
        return {"ok": True, "video_id": vid, "heygen_path": str(heygen_mp4),
                "local_path": str(local),
                "heygen_seconds": round(_get_duration(heygen_mp4, ff), 1)}
    except Exception as e:
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}


# ============================================================
# FASE C — edición final (B-roll + subs + música). Output local.
# ============================================================
def phase_c_edit(env: dict, heygen_path: str, avatar: str, slug: str,
                 lang: str = "es", broll_keywords: list = None,
                 hook_query: str = None) -> dict:
    workdir = WORK_DIR / f"{avatar}_{slug}"
    workdir.mkdir(parents=True, exist_ok=True)
    heygen_mp4 = Path(heygen_path)
    try:
        print("  [edit] gancho + B-roll (superposiciones locales) + subs ASS + música + de-click...")
        # Recursos locales por defecto (sin depender del setup con APIs):
        #   música   -> env['MUSIC_DIR']    o <cwd>/musicas
        #   b-roll    -> env['OVERLAYS_DIR'] o <cwd>/superposiciones
        music_dir = Path(env.get("MUSIC_DIR") or (Path.cwd() / "musicas"))
        overlays_dir = Path(env.get("OVERLAYS_DIR") or (Path.cwd() / "superposiciones"))
        # Gancho: imagen libre online. Si no se pasa query, se deriva del slug.
        if not hook_query:
            hook_query = slug.replace("-", " ").replace("_", " ").strip() or None
        final = burn_subs_and_music(
            heygen_mp4, music_dir, workdir / "final.mp4",
            lang=lang, env=env, broll_keywords=broll_keywords,
            overlays_dir=overlays_dir, hook_query=hook_query,
        )
        local = save_local(avatar, slug, "Video Editado", final)
        ff = get_ffmpeg_exe()
        cta = bump_success_counter()
        return {"ok": True, "final_path": str(final), "local_path": str(local),
                "final_seconds": round(_get_duration(final, ff), 1), "cta": cta}
    except Exception as e:
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}


if __name__ == "__main__":
    print("Helpers viral-pipeline (1 link → adaptaciones, salida LOCAL, por fases).")
    print("Invocar desde Claude Code: 'Sácame adaptaciones de este reel: <URL>'")
