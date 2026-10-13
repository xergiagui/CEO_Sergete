# Alta de un proyecto nuevo

Léelo solo cuando Sergio pida crear un proyecto.

## 1. Pregunta a Sergio (una sola tanda; AskUserQuestion si encaja)
- id (minúsculas, sin espacios) y nombre; tipo: `largos` o `clipping`.
- Cuenta de IG y **captura del perfil** (cabecera + primeras filas + destacadas). Si la
  pega en el chat, la imagen queda guardada en la carpeta de la sesión: pásale esa ruta a
  `perfil`, que la copia a `ThePerfil/proyectos/<id>/capturas/`.
- Plataformas y formatos (Reels / carruseles / historias); ¿blog o landing propia?
- Recursos: ¿b-roll y música propios?, ¿se permite internet? (en clipping, por defecto, no).
- Identidad: landing/enlace, parámetro de afiliado, posicionamiento, voz (persona y tono),
  palabras prohibidas, afiliación visible, marca (colores).
- Copy: CTA, ofertas y hashtags (fijos y por tema).

## 2. Alta en todos los departamentos
```
py nuevo_proyecto.py <id> --nombre "Nombre" --tipo clipping|largos --cuenta @cuenta \
   [--prefijo XX] [--descripcion "…"] [--plataformas instagram] [--formatos reels,carruseles]
```
Crea la entrada en `proyectos.json` (con `identidad` por rellenar), la carpeta del
proyecto en cada departamento y las carpetas de datos. Sale con código ≠ 0 si algún
departamento falla: no lo des por bueno.

## 3. Rellenar (en paralelo, cada subagente lo suyo)
- **CEO:** `proyectos.json` → `identidad` con lo que dijo Sergio.
- **editor:** `proyecto.json` → `recursos` y encuadre, `reglas.md`; cuando haya b-roll
  propio, el índice (`indexar_broll.py`).
- **copy:** tono del copy, ofertas, hashtags, CTA, plataformas y calendario.
- **historia:** `estilo.json` (quitar `_rellenar`), historias sí/no y crédito de carruseles.
- **perfil:** auditoría con la captura.
- **textos:** solo si hay blog.

Lo que no se sepa, se pregunta; no se inventa.

## 4. Cerrar
`py ceo.py estado --proyecto <id>` hasta que no quede nada PENDIENTE; entonces
`estado: "activo"` en `proyectos.json`. Recuérdale a Sergio dónde dejar los recursos
(`TheEditor/proyectos/<id>/recursos/`) y los vídeos (`…/input/`, los clips por carpetas).
