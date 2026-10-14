# ThePerfil

Departamento de **CEO_Sergete** que revisa el perfil de Instagram de cada
proyecto (foto, nombre, @, bio, enlace, categoría, destacadas, primeras 9 y
fijados) a partir de una captura, y propone cambios concretos antes → después.

- **Por proyecto:** `proyectos/<id>/` con `perfil.json`, `capturas/` y `auditorias/`. La identidad
  (cuenta, enlace, voz, palabras prohibidas, marca) se lee de `CEO_Sergete/proyectos.json`.
- **Checklist:** [`referencias/checklist_perfil.md`](referencias/checklist_perfil.md).
- **Validador** (sin dependencias): comprueba nombre ≤ 30, bio ≤ 150, destacadas
  ≤ 15 y las reglas del proyecto (afiliación, palabras prohibidas, emojis).

```powershell
py validar_perfil.py --proyecto mongemalo --nombre "Sergio | Ventas y copywriting" `
   --bio "Línea 1\nLínea 2" --destacada "Empieza aquí" --destacada "Cursos"
```

Proyecto nuevo: copia `proyectos/_plantilla/` a `proyectos/<id>/` y rellena
`perfil.json`. Reglas de trabajo en [`CLAUDE.md`](CLAUDE.md).
