# MongeMalo — reglas propias en TheHistoria

**Identidad** (cuenta, posicionamiento, voz y tono, emojis, no suplantar,
palabras prohibidas y colores de marca): `CEO_Sergete/proyectos.json` →
`mongemalo.identidad`. Es la fuente única: no la copies aquí. Lo esencial al
escribir: de tú, y Luis Monge siempre en tercera persona (nunca hablar como él).

## Recursos
- Política de b-roll: la de `TheEditor/proyectos/mongemalo/proyecto.json`
  (`banco_comun`: `TheEditor/superposiciones/` + `match_broll`).
- Especiales: vídeos propios de Sergio en `especiales/` (git-ignored).

## Carruseles
- Crédito: `carruseles.credito` del `proyecto.json` («Ideas de Luis Monge») se
  pone solo en las fuentes de vídeo; no hace falta escribirlo en el plan.

## Fuentes de los carruseles
- Clips aprobados: `../_Historico/mongemalo/<video>/` (solo se lee, nunca se toca).
- En curso: `../TheEditor/proyectos/mongemalo/transcripciones/<video>/`.
- Artículos: `../TheTextos/textos/mongemalo/<AAAA-MM-DD>_<slug>/articulo.md`.
- Léelas con `carruseles.py --fuente <video|ruta>`. En el plan, rutas relativas
  a PruebasIA (p. ej. `_Historico/mongemalo/<video>`).

## Publicación (por script)
- Historias: `historias.py --aprobar <tanda>` → `CEO_Sergete/HISTORIAS/mongemalo/1. Pte publicar/`.
- Carruseles: `carruseles.py --aprobar <carpeta>` → `CEO_Sergete/REELS/mongemalo/1. pte Publicar/` (+ `copy`).
