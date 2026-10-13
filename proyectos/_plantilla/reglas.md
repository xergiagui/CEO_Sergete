# <Nombre> — reglas propias en TheHistoria

Qué es el proyecto, qué cuenta publica y qué se busca (rellenar).

## Recursos
- Política de b-roll: la de `TheEditor/proyectos/<id>/proyecto.json`
  (en clipping lo normal es `propio` con `internet: false`: solo
  `TheEditor/proyectos/<id>/recursos/broll/`; nada del banco común ni de internet).
- Especiales: vídeos del proyecto en `especiales/` (git-ignored). Si está vacío,
  se usa su b-roll propio (`propio`) o fondo liso (`ninguno`).

## Tono (carruseles)
- Persona (tú/usted), registro, emojis sí/no (`emojis_max` en estilo.json).
- Crédito de la fuente (`fuente.credito`) si el contenido es de otra persona.

## Fuentes de los carruseles
- `../_Historico/<id>/<video>/` (solo lectura), `../TheEditor/proyectos/<id>/…`.
- Portada: solo material del proyecto (ver `carruseles.material_extra`).

## Diseño (estilo.json)
Base genérica copiada de la plantilla: cambia colores, fuentes y `handle`.

## Publicación
- Historias OK → `CEO_Sergete/HISTORIAS/<id>/1. Pte publicar/`.
- Carruseles OK → `CEO_Sergete/REVISADOS/<id>/1. pte Publicar/` (+ `copy`).
