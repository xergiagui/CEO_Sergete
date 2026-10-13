# <Nombre> — reglas propias en TheHistoria

**Identidad** (cuenta, posicionamiento, voz y tono, emojis, no suplantar,
palabras prohibidas y colores de marca): `CEO_Sergete/proyectos.json` →
`<id>.identidad`. Es la fuente única: no la copies aquí. Si falta, TheHistoria
usa valores neutros y avisa.

## Recursos
- Política de b-roll: la de `TheEditor/proyectos/<id>/proyecto.json`
  (en clipping lo normal es `propio` con `internet: false`: solo
  `TheEditor/proyectos/<id>/recursos/broll/`; nada del banco común ni de internet).
- Especiales: vídeos del proyecto en `especiales/` (git-ignored). Si está vacío,
  se usa su b-roll propio (`propio`) o fondo liso (`ninguno`).

## Carruseles
- Crédito de la fuente: `carruseles.credito` del `proyecto.json` si el contenido
  es de otra persona (se pone solo en las fuentes de vídeo).
- Maquetación: `estilo.json` (quita `_rellenar` cuando esté revisado).

## Fuentes de los carruseles
- `../_Historico/<id>/<video>/` (solo lectura), `../TheEditor/proyectos/<id>/transcripciones/<video>/`,
  `../TheTextos/textos/<id>/<AAAA-MM-DD>_<slug>/articulo.md`.
- Léelas con `carruseles.py --fuente <video|ruta>`.
- Portada: solo material del proyecto (ver `carruseles.material_extra`).

## Publicación (por script)
- Historias: `historias.py --aprobar <tanda>` → `CEO_Sergete/HISTORIAS/<id>/1. Pte publicar/`.
- Carruseles: `carruseles.py --aprobar <carpeta>` → `CEO_Sergete/REVISADOS/<id>/1. pte Publicar/` (+ `copy`).
