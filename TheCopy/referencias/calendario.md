# Calendario de publicación

> Adaptado de sergebulaev/instagram-skills (MIT): skill `ig-content-planner` y
> sus referencias `pillars-framework`, `example-week` y `algorithm-heuristics`
> (Timing, Stories, Saves and sends). Llevado al español de España y a cómo
> trabaja TheCopy. Los valores de cada proyecto viven en
> `proyectos/<id>/proyecto.json` → `calendario` (provisionales hasta ajustarlos con
> las estadísticas de la cuenta); el código, en `lib/calendario.py`.

## La idea

- **Reels para alcance**: cada Reel llega a gente que aún no te sigue, por eso
  aguantan más frecuencia sin cansar.
- **Carruseles para guardados**: una lista, un método o un antes/después se
  guarda para volver a consultarlo.
- **Historias para la relación**: no traen alcance nuevo, pero mantienen a quien
  ya te sigue. Compartir en historias el post del día lo empuja a los seguidores
  que no lo vieron.
- **Constancia antes que volumen**: pocos posts de feed a la semana con historias a
  diario rinden más que un post diario de relleno. No se rellena por llegar a un número.
- Lo que mueve la cuenta son los **guardados** y los **compartidos**, no los «me gusta».

## Pilares y objetivos

Cada pieza lleva un **pilar** (de qué va) y un **objetivo** (qué señal busca). Son
obligatorios: en los carruseles vienen de `carrusel.json` y en los Reels los elige el
subagente `copy`. Qué significa cada valor: `proyecto.json` → `campos_extra[].ayuda`
(`copys.py brief` lo enseña). Qué objetivo rinde cada fórmula de carrusel:
`copys.py campos`.

## Qué se configura (`proyecto.json` → `calendario`)

| Clave | Para qué |
|---|---|
| `zona_horaria` | «hoy» y las horas |
| `publicaciones_semana`, `dias`, `franjas`, `segunda_franja` | cuántos posts de feed, qué días y a qué hora. La segunda franja se usa si hace falta: fecha puesta a mano sin hora en un día que ya tiene post, o más posts por semana que días |
| `balance.formato_min` | mínimo de Reels y de carruseles por semana (si hay) |
| `balance.objetivo_min`, `balance.pilar_max`, `balance.formula_max` | mínimos de objetivo, tope de pilares (p. ej. promoción) y de carruseles de la misma fórmula |
| `balance.evitar_seguidas` | no poner seguidas dos piezas del mismo vídeo de origen (`origen`) o de la misma oferta (`oferta`; la genérica no cuenta) |
| `reserva_formatos_dias`, `prioridad_tras_dias`, `semanas_por_defecto` | ver «Cómo coloca las piezas» |
| `historias.carpeta`, `historias.por_dia_min`, `historias.por_dia_max` | de dónde salen las historias y cuántas al día |

Todo el balance es recomendación: nada bloquea.

## Cómo coloca las piezas

`copys.py calendario planificar` pone fecha y hora a las piezas **registradas,
pendientes y sin fecha**, en los huecos libres **desde mañana** (o `--desde`).

0. **Primero mira las carpetas** (la misma detección que `sincronizar`): lo que está en
   *publicados* pasa a Publicado y se guarda. `hoy` y `ver` hacen lo mismo, pero solo en
   memoria. Por eso lo publicado nunca sale como atrasado ni se replanifica.
1. **Es estable.** Lo que ya tiene fecha no se mueve. Volver a ejecutarlo no
   recoloca nada: solo rellena lo nuevo.
2. **Huecos.** Cada semana tiene `publicaciones_semana` huecos: la franja de cada día
   de publicación sin post. Lo que ya está en la semana (a mano o publicado) cuenta.
3. **Para cada hueco elige**, de las piezas que esperan, la que menos reglas rompe,
   en este orden:
   - deja sitio al mínimo de cada formato. En los primeros `reserva_formatos_dias`
     solo si hay piezas de ese formato; más adelante el hueco se guarda aunque no las
     haya, para que el CEO las encargue;
   - no pasa de `formula_max` carruseles de la misma fórmula ni de `pilar_max`;
   - lo que lleva más de `prioridad_tras_dias` esperando pasa delante;
   - cubre los mínimos de objetivo cuando ya no quedan huecos de sobra;
   - evita poner seguidas dos piezas del mismo origen o de la misma oferta;
   - alterna Reel y carrusel;
   - a igualdad, la más antigua (por ID).
4. **Historias.** Reparte los archivos de la carpeta de historias, por orden de
   llegada, hasta `por_dia_min` por día y luego hasta `por_dia_max`. No mueve los
   archivos. Lo ya repartido no cambia, y lo que sale de la carpeta (publicado o
   borrado) sale del plan.
5. **Salida.** Escribe *Fecha prevista* y *Hora prevista* en el Excel, la hoja
   *Historias* y un `calendario/<AAAA>-W<ss>.md` por semana (día a día, balance y
   huecos), junto al Excel del proyecto.

## Fechas a mano

- Escribe la *Fecha prevista* (y, si quieres, la *Hora prevista*) en el Excel.
  Sin hora, se pone la franja de ese día, o la segunda si el día ya tiene post.
- Las fechas manuales **no se mueven nunca**. El planificador apunta en una hoja
  oculta (`_calendario`) las fechas que puso él; lo que no coincide con esa hoja
  es manual.
- **Atrasado** = fecha pasada, sin publicar y fuera de la carpeta de publicados.
  `calendario ver` y `calendario hoy` lo marcan. `planificar --replanificar-atrasados`
  mueve los atrasados que puso el planificador; los manuales se quedan. Para
  replanificar uno manual, borra su fecha.
- Si una fecha no se entiende (usa dd/mm/aaaa), no se toca y se avisa.

## Cuánto falta por semana

Al final de `planificar` (y de `registrar --planificar`) sale una línea para el CEO:

```
FALTAN 2026-W43 reels=1 carruseles=1 cualquiera=1 huecos=3 historias=14 | 2026-W44 …
```

`huecos` son los posts libres de la semana; `reels` y `carruseles`, los que faltan
para el mínimo de cada formato; `cualquiera`, el resto de huecos (Reel o carrusel);
`historias`, las que faltan para llegar a `por_dia_min` al día. `--json` da lo mismo
en el campo `faltan` con el detalle por semana.

## Órdenes

```powershell
.venv\Scripts\python.exe copys.py calendario planificar [--semanas N] [--desde AAAA-MM-DD] [--simular] [--replanificar-atrasados] [--json]
.venv\Scripts\python.exe copys.py calendario hoy [--fecha AAAA-MM-DD]
.venv\Scripts\python.exe copys.py calendario ver [--semana AAAA-Www]
```

Para pruebas: `--excel <ruta>` (los `.md` van a `<carpeta del Excel>/calendario/`),
`--pendiente`, `--publicado` y `--carpeta-historias <ruta>`.
