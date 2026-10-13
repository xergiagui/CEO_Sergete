# <Nombre>: reglas de edición del proyecto

Proyecto `<id>`. Estas reglas se suman a las generales de `TheEditor/CLAUDE.md`
(que valen para todos). Aquí va solo lo propio de este proyecto.

## Qué es
- Cuenta o cliente, plataforma y objetivo de los clips. PENDIENTE
- Tipo: `clipping` (vídeos ya cortados) o `largos`. PENDIENTE

## Protagonista
- Quién sale y cómo reconocerlo (para centrar el encuadre). PENDIENTE

## Recursos (`proyecto.json → recursos`)
- Clipping: **solo** los recursos del proyecto. B-roll en `recursos/broll/`
  (subcarpetas permitidas; lo que empieza por `_` se ignora), música en
  `recursos/musica/` (suelta o en subcarpetas por tipología: «motivacion»,
  «epica»…), click opcional en `recursos/sfx/`. Nada de internet.
- Para casar el b-roll por significado: `indexar_broll.py --proyecto <id> --frames`,
  describir cada clip en `recursos/broll/_descripciones.json` e
  `indexar_broll.py --proyecto <id>` (crea `_indice.json`). Sin índice no hay casación
  por significado: como mucho 1 b-roll al azar por clip.

## Encuadre (vía 2)
- Modo por carpeta de `input/` en `proyecto.json → encuadre.carpetas`.
  PENDIENTE

## Tono y textos
- Tono de los ganchos de texto, palabras o temas que evitar. PENDIENTE
