# Auditoría del copy antes de registrar

> Adaptado de sergebulaev/instagram-skills (MIT): `ig-humanizer` V3 (scrub-rules,
> audit-checklist, post-audit) y `ig-hashtag-strategist`. Llevado al español de
> España y a captions cortos de Reel (1–3 frases + CTA). Vale para todos los
> proyectos; los límites de cada uno están en su `proyecto.json`.

## Cómo se usa

```powershell
.venv\Scripts\python.exe copys.py auditar --entrada tandas\<tanda>.json   # la tanda rellena
.venv\Scripts\python.exe copys.py auditar --texto "Un copy suelto. Link en bio."
.venv\Scripts\python.exe copys.py auditar --banco                          # banco_copys.json
```

`auditar` solo informa: no reescribe nada. `registrar` pasa la misma auditoría.

**Solo estilo (texto de las slides de un carrusel, lo usa TheHistoria):**

```powershell
.venv\Scripts\python.exe copys.py auditar --solo-estilo --json --texto "<texto de la slide>"
```

`--solo-estilo` aplica solo los puntos 2–8 (cebos y cierres vacíos como error; estilo y
emojis como aviso): ni gancho de 125, ni CTA, ni hashtags, ni longitud de plataforma.
`--json` saca por stdout una lista `[{"nivel", "regla", "fragmento", "mensaje"}]` en ASCII
(los acentos van como `á`); sale con código 0 si no hay errores y 1 si los hay.

En un **carrusel**, el caption repite el gancho de la slide 1: lo que sale tal cual en las
slides cuenta como literal (igual que lo que se dice en un clip).

- **Error**: bloquea el registro.
- **Aviso de estilo**: no bloquea, pero **se corrige reescribiendo antes de
  registrar**. Solo se deja si la frase es **literal del clip** (sale en
  `contexto.frase_viral` o `contexto.transcripcion`); entonces aparece como
  «literal del clip, se permite» y no cuenta como aviso.

## Bloqueantes (error)

1. **Gancho largo.** El gancho es la primera frase o la primera línea (lo que
   acabe antes). Si pasa de `gancho_max` (Instagram: 125), el «más» lo corta.
   - Mal: «"No tengo dinero", "lo tengo que pensar"... si cada objeción te
     paraliza, no tienes un problema de producto, tienes un problema de guion.»
   - Bien: «"No tengo dinero", "lo tengo que pensar", "mándamelo por escrito".»
2. **Cebo de interacción.** Instagram lo penaliza: «comenta SÍ», «comenta YO»,
   «comenta "GUÍA"», «escribe QUIERO en los comentarios», «etiqueta a ese
   amigo…», «dale like», «doble tap», «comparte si…» / «si te ha gustado,
   compártelo».
3. **Cierre vacío.** Preguntas genéricas que no aportan: «¿qué opinas?», «¿tú
   qué piensas?», «¿estás de acuerdo?», «¿y tú?», «¿lo sabías?». El cierre es el
   CTA del proyecto.

`registrar` también da error si falta el CTA, hay hashtags dentro del copy, se
pasa la longitud de la plataforma o el copy ya está registrado.

## Avisos de estilo (se corrigen)

4. **Paralelismo negativo.** Dilo en positivo, sin contraponer «no X / sí Y».
   - «No necesitas más seguidores. Necesitas saber convertir los que ya tienes.»
     → «Los seguidores que ya tienes te bastan para vender, si sabes convertirlos.»
   - «Esto no va de suerte, va de técnica.» → «Lo que ves aquí es técnica, y la
     técnica se entrena.»
   - También: «El problema no es X, es Y», «No se trata de X. Se trata de Y.»,
     «no es X sino Y», «Sin X. Sin Y. Solo Z.», «Deja de X. Empieza a Y.»
5. **Revelaciones.** El puente que anuncia lo que viene: «¿El resultado?», «¿La
   clave?», «¿Por qué? Porque…», «¿Sabes qué?», «Spoiler:», «Esto es lo que
   nadie te cuenta:», «Aquí tienes cómo.» Quita el puente y deja la frase que
   venía después.
6. **Anuncio de sinceridad al abrir una frase.** «Te voy a ser sincero», «seamos
   sinceros», «no te voy a mentir», «hablemos claro», «la verdad es que…», «la
   cruda realidad», «opinión impopular:». Bórralo y empieza por el hecho.
7. **Vocabulario de IA por densidad.** Una palabra suelta no es nada; dos o más
   en el mismo párrafo, sí: fundamental, crucial, esencial, potenciar, impulsar,
   transformar, desbloquear, descubre, sin duda, en definitiva, en el mundo
   actual, hoy en día, llevar al siguiente nivel, sumérgete, exponencial,
   ecosistema, sinergia, un antes y un después… Cámbialas por algo concreto del
   clip o quítalas (no por un sinónimo de la misma lista).
8. **Emojis** por encima de `emojis_max` de la plataforma (MongeMalo: 0).

## Revisión a ojo (no automática)

- Fragmentos para dramatizar («Punto.», «Así de simple.») y escaleras tipo
  «Directo. Claro. Rentable.»: como mucho 2 frases sueltas por copy.
- Tríadas huecas («más rápido, más fácil y mejor»). Una enumeración concreta
  («"no tengo dinero", "lo tengo que pensar", "mándamelo por escrito"») vale.
- Rayas (—): como mucho una en un copy corto.
- Un solo CTA, y que sea el del proyecto.
- Mejor un dato concreto del clip que un adjetivo. Nunca cifras inventadas.

## Al reescribir

- Toca solo lo marcado; conserva la idea, el tono y el CTA.
- No añadas dudas ni confesiones impostadas («quizá me equivoque, pero…»).
- No metas otro patrón al quitar uno (p. ej. cambiar un paralelismo por «Sin
  X. Sin Y.»). Vuelve a pasar `auditar` después de reescribir.

## Hashtags (Instagram)

- 3–5 en total contando los fijos: 2–3 de nicho (< 50k publicaciones), 1–2
  medios (50k–500k) y como mucho 1 amplio (> 500k). `registrar` da error si el
  total se sale del rango o hay más amplios de la cuenta.
- Todos acordes al tema del clip; nada de etiquetas de relleno (#follow4follow,
  #like4like…).
- Rota por tema: no repitas el mismo conjunto que otro clip de la tanda ni que
  los últimos registrados (`copys.py hashtags` los enseña).
- Los tamaños de `hashtags.json` son **estimados**: verifícalos en el buscador
  de Instagram cuando haya dudas.
