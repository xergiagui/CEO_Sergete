# ThePerfil — Departamento de perfiles

Revisa el **perfil de Instagram de cada proyecto** a partir de una captura y
propone cambios concretos (antes → después). Lo dirige CEO_Sergete con el
subagente `perfil`. **Este archivo manda** sobre las reglas de trabajo.

## Cuándo se usa
- **Al crear un proyecto nuevo:** el CEO pide a Sergio una captura del perfil
  (cabecera + primeras filas de la cuadrícula + destacadas) y lanza `perfil`.
- **A demanda:** «revisa mi perfil», «mejora la bio», «qué destacadas pongo».
- **Para comparar:** tras aplicar cambios, una captura nueva queda en el historial.

## Entorno
Sin dependencias: `py validar_perfil.py ...` (librería estándar). Nunca `python3`
(en este equipo es el acceso directo de la Microsoft Store).

## Estructura (un proyecto = una carpeta)
```
proyectos/<id>/
  perfil.json        cuenta, objetivo, enlace de destino, posicionamiento, marca, reglas, historial
  capturas/          AAAA-MM-DD_<qué>.png  (cabecera, cuadricula, destacadas…)
  auditorias/        AAAA-MM-DD.md         una por revisión
proyectos/_plantilla/   se copia para un proyecto nuevo
referencias/checklist_perfil.md            las 9 partes y cómo se puntúan
```

## Flujo de una revisión
1. Lee `referencias/checklist_perfil.md` y `proyectos/<id>/perfil.json`. Si el
   proyecto no existe, copia `proyectos/_plantilla/` y pregunta al CEO lo que
   falte (cuenta, objetivo, enlace, posicionamiento, reglas); no lo inventes.
2. Guarda la captura en `capturas/AAAA-MM-DD_<qué>.png`.
3. Puntúa las 9 partes (Bien / Mejorable / Suspenso / **Sin datos** si la
   captura no la muestra; nunca supongas).
4. Propón cambios ordenados por impacto. Para bio y nombre, 2–3 opciones,
   **validadas** con:
   `py validar_perfil.py --proyecto <id> --nombre "..." --bio "línea\nlínea" [--destacada "..."]`
5. Escribe `auditorias/AAAA-MM-DD.md` (corta: tabla de 9 partes, cambios,
   decisiones para Sergio y pendientes) y añade la entrada a `historial`.
6. Si la revisión anterior existe, di qué ha mejorado y qué sigue igual.

## Reglas
- Coherencia con el resto del sistema: el **enlace** debe ser el destino de los
  CTA de los copys (TheCopy) y la **marca** la de carruseles e historias.
- Respeta las `reglas` del proyecto (afiliación visible, palabras prohibidas,
  emojis, no suplantar). En MongeMalo: perfil independiente, nunca «trabajando
  para» ni promesas de resultados.
- No inventes cifras, resultados ni testimonios. Los cambios los aplica Sergio en
  la app: tú solo propones.

## Qué devuelve al CEO
Ruta de la auditoría, la tabla de 9 partes resumida, los 3 cambios con más
impacto (con el texto exacto) y lo que falta (capturas o decisiones).
