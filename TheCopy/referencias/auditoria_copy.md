# Auditoría del copy antes de registrar

> Adaptado de sergebulaev/instagram-skills (MIT): `ig-humanizer` V3 (scrub-rules,
> audit-checklist, post-audit) y `ig-hashtag-strategist`. Llevado al español de
> España y a captions cortos de Reel (1–3 frases + CTA). Vale para todos los
> proyectos: los límites de cada uno están en su `proyecto.json` y su identidad
> (voz, emojis, palabras prohibidas) en `CEO_Sergete/proyectos.json`. El código
> es `lib/auditoria.py`; esto es la explicación para personas.

## Cómo se usa

```powershell
.venv\Scripts\python.exe copys.py registrar --entrada tandas\<id>\<tanda>.json --simular   # lo normal
.venv\Scripts\python.exe copys.py auditar --entrada tandas\<id>\<tanda>.json
.venv\Scripts\python.exe copys.py auditar --proyecto <id> --texto "Un copy suelto. Link en bio."
.venv\Scripts\python.exe copys.py auditar --proyecto <id> --banco                     # banco_copys.json
```

`auditar` solo informa: no reescribe nada. `registrar` pasa la misma auditoría.

**Solo estilo (texto de las slides de un carrusel, lo usa TheHistoria):**

```powershell
.venv\Scripts\python.exe copys.py auditar --solo-estilo --json --proyecto <id> --texto "<slide 1>" --texto "<slide 2>"
'["<slide 1>", "<slide 2>"]' | .venv\Scripts\python.exe copys.py auditar --solo-estilo --json --proyecto <id> --stdin
```

`--solo-estilo` aplica solo los puntos 2–10 (cebos, cierres vacíos y palabras prohibidas como
error; estilo, emojis y primera persona como aviso): ni gancho, ni CTA, ni hashtags, ni longitud.
`--json` saca por stdout una lista `[{"i", "nivel", "regla", "fragmento", "mensaje"}]` en ASCII
(`i` = índice del texto; los acentos van como `á`); sale con 0 si no hay errores y 1 si los
hay. Sin `--proyecto` no se aplica la identidad.

- **Error**: bloquea el registro.
- **Aviso de estilo**: no bloquea (salvo `registrar --estricto`), pero **se corrige
  reescribiendo antes de registrar**. Solo se deja si la frase es **literal del clip**
  (`contexto.frase_viral` o `contexto.transcripcion`) o de las slides del carrusel; entonces
  aparece como «literal del clip, se permite» y no cuenta como aviso.

## Bloqueantes (error)

1. **Gancho largo.** El gancho es la primera frase o la primera línea (lo que
   acabe antes). Si pasa de `gancho_max` de la plataforma, el «más» lo corta.
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
4. **Palabra prohibida** de la identidad (`palabras_prohibidas`), sin distinguir
   tildes ni mayúsculas. No tiene excepción de literal. También en el título.

`registrar` también da error si falta el CTA, hay hashtags dentro del copy, se
pasa la longitud de la plataforma o el copy ya está registrado.

## Avisos de estilo (se corrigen)

5. **Paralelismo negativo.** Dilo en positivo, sin contraponer «no X / sí Y».
   - «No necesitas más seguidores. Necesitas saber convertir los que ya tienes.»
     → «Los seguidores que ya tienes te bastan para vender, si sabes convertirlos.»
   - «Esto no va de suerte, va de técnica.» → «Lo que ves aquí es técnica, y la
     técnica se entrena.»
   - También: «El problema no es X, es Y», «No se trata de X. Se trata de Y.»,
     «no es X sino Y», «Sin X. Sin Y. Solo Z.», «Deja de X. Empieza a Y.»
6. **Revelaciones.** El puente que anuncia lo que viene: «¿El resultado?», «¿La
   clave?», «¿Por qué? Porque…», «¿Sabes qué?», «Spoiler:», «Esto es lo que
   nadie te cuenta:», «Aquí tienes cómo.» Quita el puente y deja la frase que
   venía después.
7. **Anuncio de sinceridad al abrir una frase.** «Te voy a ser sincero», «seamos
   sinceros», «no te voy a mentir», «hablemos claro», «la verdad es que…», «la
   cruda realidad», «opinión impopular:». Bórralo y empieza por el hecho.
8. **Vocabulario de IA por densidad.** Una palabra suelta no es nada; dos o más
   en el mismo párrafo, sí: fundamental, crucial, esencial, potenciar, impulsar,
   transformar, desbloquear, descubre, sin duda, en definitiva, en el mundo
   actual, hoy en día, llevar al siguiente nivel, sumérgete, exponencial,
   ecosistema, sinergia, un antes y un después… Cámbialas por algo concreto del
   clip o quítalas (no por un sinónimo de la misma lista).
9. **Emojis** por encima de `emojis_max` (`identidad.voz.emojis_max`, salvo que la
   plataforma lo sobrescriba).
10. **Primera persona del singular** («yo», «me», «mi», «tengo», «aprendí», «probé»…)
    si la identidad define `voz.persona`: quien publica no es quien sale en el clip.
    Se escribe de tú al lector y a la persona del clip en tercera. No cuenta lo que
    va entre comillas (una objeción del cliente, una cita) ni la frase literal del clip.
    - «Esto es lo que a mí me costó años entender.» → «Esto resume lo que a él le costó
      años entender.»

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
  X. Sin Y.»). Vuelve a pasar `registrar --simular` después de reescribir.

## Hashtags

- Las cifras (temáticos, total con los fijos, mínimo de nicho, máximo de amplios,
  rotación) están **solo** en `proyecto.json` → `plataformas.<p>.hashtags`;
  `copys.py brief` y `copys.py hashtags` las enseñan tal y como las comprueba el código.
- Lo normal es no escribirlos: con `hashtags_temas` en la pieza, `registrar` elige un
  conjunto válido, acorde al tema y rotado.
- Si se escriben a mano: todos acordes al tema del clip, nada de etiquetas de relleno
  (#follow4follow, #like4like…) y sin repetir el conjunto de otra pieza de la tanda ni
  de los últimos registrados.
- Los tamaños de `hashtags.json` son **estimados**: verifícalos en el buscador
  de Instagram cuando haya dudas.
