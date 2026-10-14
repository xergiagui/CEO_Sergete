# Viral Pipeline v1 — guía rápida para el cliente

Sistema que toma UN link de viral (IG/TikTok/YouTube) y genera **adaptaciones** con tu avatar IA y tu voz clonada. La salida queda en tu Mac/PC, sin depender de ningún servicio externo de base de datos.

## Lo que necesitas tener

| | |
|---|---|
| **Cuenta HeyGen** | API (pay-as-you-go; carga ~$15-20 en wallet). Avatar V = mejor calidad/más caro; Avatar IV = más barato |
| **Cuenta ElevenLabs** | Starter ($5/mes) — incluye voice cloning + API |
| **Cuenta Pexels** | Free, registro instantáneo (para el B-roll) |
| **macOS, Linux o Windows** | Python 3 ya viene preinstalado en Mac/Linux |

**No necesitas instalar nada más.** La skill se encarga del resto.

## Setup (una sola vez, ~3 minutos)

Abre Claude Code en cualquier carpeta y di:

```
monta el viral pipeline
```

Claude, por popups:
1. **Instala** todas las deps en un entorno aislado (no toca tu Python del sistema)
2. Te pide: keys de API (HeyGen, ElevenLabs, Pexels), la **voz** clonada de tu cuenta, el **engine HeyGen** (Avatar V o IV) y su **ID de look**, nombre/idioma/estilo, y una **descripción de tu avatar**
3. Guarda todo en `~/.viral-pipeline/env.json` para próximas conversaciones

> **Avatar V vs IV:** Avatar V da mejor lip-sync pero la foto debe **subirse por la web de heygen.com** (por API no se puede crear) y mirar a cámara. Avatar IV es más barato y vale aunque no mire de frente. La skill te lo pregunta y verifica el look.

## Uso diario

Una vez configurado, en cualquier conversación de Claude Code:

```
sácame adaptaciones de este reel: https://instagram.com/reel/XXXX
```

Claude:
1. Descarga + transcribe el reel
2. Te muestra el patrón narrativo del original (hook → desarrollo → CTA)
3. Te propone 3 guiones distintos (mismo patrón, 3 ángulos), usando tu descripción de avatar
4. Eliges: **avanzar con 1, 2, 3 o los 3** (o escribes qué cambiar)
5. Procesa **por fases con aprobación en cada una**: audio → (apruebas) → avatar HeyGen → (apruebas) → edición final

## Cómo termina cada vídeo

Cada adaptación queda en una carpeta legible en tu equipo:

```
~/Desktop/viral_pipeline_output/<TuAvatar>/<nombre-del-video>/
   Audio__audio_final.mp3        ← la voz
   Video Heygen__heygen.mp4      ← el avatar
   Video Editado__final.mp4      ← el final con subs karaoke + B-roll + música (el que publicas)
```

La subcarpeta lleva el **nombre del vídeo** (no "Video 1/2"), así no se lía si descontinúas una serie.

## Costes (orientativo)

- **Avatar IV**: ~€1.40 por vídeo de 30s (HeyGen $0.05/s). **Avatar V** cuesta más por segundo.
- **ElevenLabs**: ~€5/mes (Starter). **Pexels + edición**: gratis (ffmpeg incluido).

## Troubleshooting

- Si una adaptación falla, lo verás en la conversación con el error. Reintenta esa fase.
- Tu copia local siempre queda guardada en `~/Desktop/viral_pipeline_output/`.
