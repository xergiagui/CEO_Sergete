# MongeMalo: reglas de edición del proyecto

Perfil de afiliado de Luis Monge (`@xergi.ventas`). Clips de ventas,
copywriting, emprendimiento y dinero que llevan tráfico a sus cursos con el
enlace de afiliado de Sergio. Tipo `largos`: vídeos largos de YouTube que baja
TheDescarga (vía 1) o que llegan ya en extractos «Largo N Extractos» (vía 2).

Estas reglas se suman a las generales de `TheEditor/CLAUDE.md`.

## Identidad y tono
- Perfil **independiente**, no la cuenta oficial de Luis: no imitar su
  identidad. Transparencia de afiliación y nada de prometer resultados
  económicos.

## Protagonista
- **Luis Monge** = hombre de pelo oscuro, barba corta y ropa North Face (no el
  calvo ni el señor canoso). Todos sus clips, centrados en él.

## Recursos (`proyecto.json → recursos`)
- Banco común: b-roll de `superposiciones/` (catálogo `broll_assets` + RPC
  `match_broll`), música de `musicas/`, gancho visual de Pexels al inicio
  (vía 1) y gancho de texto. Guarda frases en `viral_phrases` con la etiqueta
  `proyecto:mongemalo`.

## Encuadre de los extractos (vía 2)
Los extractos van en `proyectos/mongemalo/input/<Largo N Extractos>/`. El modo de
cada carpeta está en `proyecto.json → encuadre.carpetas` y el batch lo toma
solo si no se le pasa `MODO`:

| Carpeta | Plano | Modo |
|---|---|---|
| Largo 1 | a dos, estático, Luis a la derecha | `right` |
| Largo 2, 3, 6, 7 | Luis solo | `follow` |
| Largo 4 | multicámara a 3 (Luis a la izquierda) | `auto` |
| Largo 5 | multicámara a 2, primeros planos alternos | `follow` |

Carpeta nueva sin modo en el mapa: `right` (`encuadre.modo_por_defecto`).
Revisa el plano y, si hace falta, añádela al mapa.

## Histórico
Los clips aprobados (vídeos largos y «Largo 1–7 Extractos») están en
`PruebasIA/_Historico/mongemalo/`.
