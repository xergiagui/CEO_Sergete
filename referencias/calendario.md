# Calendario de publicación

> Adaptado de sergebulaev/instagram-skills (MIT): skill `ig-content-planner` y
> sus referencias `pillars-framework`, `example-week` y `algorithm-heuristics`
> (Timing, Stories, Saves and sends). Llevado al español de España y a cómo
> trabaja TheCopy. La configuración vive en `proyectos/<id>/proyecto.json` →
> `calendario`; el código, en `lib/calendario.py`.

## La idea

- **Reels para alcance**: cada Reel llega a gente que aún no te sigue, por eso
  aguantan más frecuencia sin cansar.
- **Carruseles para guardados**: una lista, un método o un antes/después se
  guarda para volver a consultarlo.
- **Historias para la relación**: no traen alcance nuevo, pero mantienen a quien
  ya te sigue. Compartir en historias el post del día lo empuja a los seguidores
  que no lo vieron.
- **Constancia antes que volumen**: 4–5 posts de feed a la semana con historias a
  diario rinden más que un post diario de relleno. No se rellena por llegar a un número.
- Lo que mueve la cuenta son los **guardados** y los **compartidos**, no los «me gusta».

## Pilares y objetivos

Cada pieza lleva un **pilar** (de qué va) y un **objetivo** (qué señal busca).
Son obligatorios: en los carruseles vienen de `carrusel.json` y en los Reels los
elige el subagente `copy` al escribir el copy.

| Pilar | Para qué | Objetivo habitual |
|---|---|---|
| `educativo` | enseñar lo que da fama a la cuenta | guardados |
| `historia` | experiencia en primera persona, aciertos y errores | seguidores, comentarios |
| `interaccion` | situaciones con las que la audiencia se identifica | comentarios, compartidos |
| `promocion` | el producto, la oferta, el siguiente paso | seguidores |

`promocion` solo cuando la pieza va **sobre todo** de vender un producto. Nombrar
la oferta en el caption no convierte la pieza en promoción. Tope: 1–2 por semana,
porque el exceso se come el alcance.

Fórmulas de carrusel (contrato con TheHistoria): `IG5_lista` y `IG8_metodo` →
guardados; `IG6_antes_despues` → guardados y seguidores; `IG7_mitos` → compartidos.

## Valores de MongeMalo (provisionales)

Salen de las franjas genéricas del método (días laborables a mediodía y a última
hora, más el domingo por la tarde) y **hay que ajustarlos con las estadísticas de
la cuenta** (Insights de Instagram: a qué horas está conectada la audiencia y qué
formatos se guardan y se comparten más).

- Zona horaria `Europe/Madrid`.
- **5 posts de feed por semana**: lunes, martes, jueves, viernes y domingo.
- Franjas: **13:30** de lunes a viernes y **20:30** el domingo. La segunda franja
  (20:30) se usa si hace falta: una fecha puesta a mano sin hora en un día que ya
  tiene post, o si algún día se piden más posts por semana que días de publicación.
- Por semana: **≥ 2 Reels y ≥ 2 carruseles** (si hay), **≥ 3 de guardados**,
  **≥ 2 de compartidos**, **promoción ≤ 2**, no más de **2 carruseles de la misma
  fórmula** y no poner seguidas dos piezas del **mismo vídeo de origen** ni de la
  **misma oferta** (la genérica no cuenta). Todo es recomendación: nada bloquea.
- **Historias: 2–4 al día**, de `CEO_Sergete/HISTORIAS/1. Pte publicar`, más el
  recordatorio diario de compartir el post del día en historias.

## Cómo coloca las piezas

`copys.py calendario planificar` pone fecha y hora a las piezas **registradas,
pendientes y sin fecha**, en los huecos libres **desde mañana** (o `--desde`).

1. **Es estable.** Lo que ya tiene fecha no se mueve. Volver a ejecutarlo no
   recoloca nada: solo rellena lo nuevo.
2. **Huecos.** Cada semana tiene 5 huecos: la franja de cada día de publicación
   sin post. Lo que ya está en la semana (a mano o publicado) cuenta para los 5.
3. **Para cada hueco elige**, de las piezas que esperan, la que menos reglas rompe,
   en este orden:
   - deja sitio al mínimo de cada formato. En los primeros 7 días
     (`reserva_formatos_dias`) solo si hay piezas de ese formato; más adelante el
     hueco se guarda aunque no las haya, para que el CEO las encargue;
   - no pasa de 2 carruseles de la misma fórmula ni de 2 piezas de promoción;
   - lo que lleva más de 14 días esperando (`prioridad_tras_dias`) pasa delante;
   - cubre los mínimos de guardados y compartidos cuando ya no quedan huecos de sobra;
   - evita poner seguidas dos piezas del mismo origen o de la misma oferta;
   - alterna Reel y carrusel;
   - a igualdad, la más antigua (por ID).
4. **Historias.** Reparte los archivos de la carpeta de historias, por orden de
   llegada, hasta 2 por día y luego hasta 4. No mueve los archivos. Lo ya repartido
   no cambia, y lo que sale de la carpeta (publicado o borrado) sale del plan.
5. **Salida.** Escribe *Fecha prevista* y *Hora prevista* en el Excel, la hoja
   *Historias* y un `calendario/<AAAA>-W<ss>.md` por semana (día a día, balance y
   huecos), junto al Excel del proyecto.

## Fechas a mano

- Escribe la *Fecha prevista* (y, si quieres, la *Hora prevista*) en el Excel.
  Sin hora, se pone la franja de ese día, o la segunda si el día ya tiene post.
- Las fechas manuales **no se mueven nunca**. El planificador apunta en una hoja
  oculta (`_calendario`) las fechas que puso él; lo que no coincide con esa hoja
  es manual.
- **Atrasado** = fecha pasada y sin publicar. `calendario ver` y `calendario hoy`
  lo marcan. `planificar --replanificar-atrasados` mueve los atrasados que puso
  el planificador; los manuales se quedan. Para replanificar uno manual, borra su fecha.
- Si una fecha no se entiende (usa dd/mm/aaaa), no se toca y se avisa.

## Cuánto falta por semana

Al final de `planificar` sale una línea para el CEO:

```
FALTAN 2026-W43 reels=1 carruseles=1 cualquiera=1 huecos=3 historias=14 | 2026-W44 …
```

`huecos` son los posts libres de la semana; `reels` y `carruseles`, los que faltan
para el mínimo de cada formato; `cualquiera`, el resto de huecos (Reel o carrusel);
`historias`, las que faltan para llegar a 2 al día. `--json` da lo mismo en el campo
`faltan` con el detalle por semana.

## Órdenes

```powershell
.venv\Scripts\python.exe copys.py calendario planificar [--semanas N] [--desde AAAA-MM-DD] [--simular] [--replanificar-atrasados] [--json]
.venv\Scripts\python.exe copys.py calendario hoy [--fecha AAAA-MM-DD]
.venv\Scripts\python.exe copys.py calendario ver [--semana AAAA-Www]
```

Para pruebas: `--excel <ruta>` (los `.md` van a `<carpeta del Excel>/calendario/`)
y `--carpeta-historias <ruta>`.
