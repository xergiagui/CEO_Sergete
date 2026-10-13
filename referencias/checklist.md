# Checklist de TheTextos

> Basado en las skills blog-* (oct. 2026); revisar cada trimestre.
>
> Sustituye a los SKILL.md en el día a día. Vale para un **borrador en Markdown
> sin blog publicado**: lo que depende del sitio es N/A.

## 1. Redacción

- **Answer-first.** Las 1–2 primeras frases del artículo responden a la
  búsqueda y cada H2 abre con su respuesta directa. Que se entienda aunque una
  IA cite solo ese párrafo: nombra la entidad («El seguimiento comercial es…»),
  nada de «como vimos arriba».
- **Intro** de 100–150 palabras: problema del lector, respuesta corta y qué va
  a encontrar. La keyword, en las primeras 100 palabras.
- **Puntos clave**, justo tras la intro y antes del primer H2: un bloque
  `> **Puntos clave**` con 3–5 viñetas que se entiendan sin leer el resto. Con
  cifras solo si están en la tabla de datos.
- **Párrafos:** la idea principal en la primera frase; un tema por párrafo.
  Alterna frases cortas y largas; parte la frase que cueste seguir.
- **Definiciones:** la primera vez que sale un concepto, «X es…». El mismo
  nombre para la misma cosa en todo el texto.
- **Formato:** lista numerada para pasos, tabla con cabecera para comparar,
  listas solo con 3 o más elementos paralelos. Negrita con moderación (menos
  del 10 % del texto).
- **Cifras:** solo las de la tabla de datos del brief, con la fuente enlazada
  junto al dato y su año: «el 42 % (…) ([Fuente](url), 2026)».
- **Experiencia:** nunca inventes primera persona («cuando lo probé…») ni
  casos. Solo si el autor aporta la evidencia. Nada de «como experto…».
- **FAQ:** solo preguntas reales (las PAA del brief), de 3 a 5. Cada respuesta
  empieza por la respuesta y se entiende sola.
- **Cierre:** sin resumen que repita el artículo. Un siguiente paso concreto y
  un solo CTA, después de aportar valor.
- **Puntuación:** la raya de inciso (—así—) está permitida en español; úsala
  con moderación y nunca para pegar dos oraciones (ahí va punto o dos puntos).
  Comillas españolas « ».
- **Voz:** la de `marca/VOICE.md` o, si está PENDIENTE, la provisional
  (`identidad.voz`: persona y tono). Español de España.

### Muletillas de IA en español

Evítalas al escribir. El paso 3 las busca con `grep` (un patrón por línea; un
acierto no obliga a cambiar, pero casi siempre hay una forma más directa):

```muletillas
en el mundo (actual|de hoy|digital|moderno)
en la era (digital|actual|moderna)
en el (vertiginoso|cambiante|competitivo) mundo
hoy en día
es (importante|fundamental|clave) (destacar|señalar|recordar|tener en cuenta)
cabe (destacar|mencionar|señalar|resaltar)
vale la pena (destacar|mencionar)
juegan? un papel
sin lugar a dudas
en este sentido
en definitiva
en conclusión
no solo .* sino (también|que)
a la hora de
sumerg|sumérg
adéntrate
desbloque
potenciar|potencia tu
aprovechar al máximo|aprovecha al máximo
panorama
robust[oa]
integral
siguiente nivel
un mundo de posibilidades
navegar (por|el|la)
el arte de
revolucion
fomentar
crucial
exhaustiv
sinergia
descubre cómo
¿el resultado\?
te voy a ser sincer
la verdad es que
```

Tampoco: paralelismos negativos («No es X, es Y», «Sin X. Sin Y. Solo Z.»),
tríadas forzadas en cada frase ni cierres del tipo «el futuro es prometedor».

## 2. GEO: 7 puntos (pasa / no pasa)

1. **Respuesta directa:** las dos primeras frases responden a la keyword y
   cada H2 abre con su respuesta.
2. **Pasajes autocontenidos:** cada sección se entiende citada sola (entidad
   nombrada, sin «esto» ni «lo anterior» sin referente).
3. **Afirmación + apoyo:** al menos el 80 % de las secciones tiene una
   afirmación concreta con apoyo verificable (dato con fuente y año, ejemplo o
   definición precisa).
4. **Entidad clara:** un solo tema, definido en la intro («X es…»), con el
   mismo nombre en todo el texto; el título refleja el contenido.
5. **Estructura extraíble:** «Puntos clave» y al menos 3 de estos: lista
   numerada, tabla con cabecera, definiciones, FAQ, explicación con evidencia.
6. **Frescura y autoría visibles:** `date`, `lastUpdated` y autor; cifras con
   su año, de la edición más reciente.
7. **Schema = texto visible:** `schema.json` coincide con title, description,
   fechas, autor y FAQ.

N/A en borrador: acceso de los crawlers (robots, renderizado). En el informe:
`GEO X/7`.

## 3. SEO on-page: 12 puntos

1. **Title** de 60 caracteres como máximo, keyword al principio; describe lo
   que hay, sin exagerar.
2. **Description** de 140–160 caracteres: resume lo visible, keyword natural,
   nada que el texto no cumpla.
3. **Un solo H1** (el título), con la keyword.
4. **H2/H3** sin saltar niveles; H2 descriptivos o en pregunta según la
   intención, cada uno conectado con su sección.
5. **Keyword en el primer párrafo** (primeras 100 palabras).
6. **Keyword o variante en 1–3 H2**, secundarias repartidas, sin forzar.
7. **Slug:** minúsculas, guiones, sin tildes ni ñ, sin fecha, 3–6 palabras
   con la keyword (`como-gestionar-objeciones`).
8. **2–5 enlaces externos** a fuentes T1–T3, con ancla descriptiva, cada URL
   una sola vez y sin competidores directos.
9. **Enlaces internos:** zonas `[ENLACE-INTERNO: ancla → destino]` en la
   intro, los H2 y el cierre (3–5); con la URL real si está en
   `enlaces_internos`. Nunca «haz clic aquí».
10. **Imágenes:** si se proponen, `[IMAGEN: qué muestra | alt: frase
    descriptiva]`; si no hay, N/A.
11. **Frontmatter completo** (campos en `CLAUDE.md`), `lastUpdated` igual o
    posterior a `date` y 3–6 `tags`.
12. **Intención cubierta sin relleno:** más de 500 palabras (o lo que fije el
    tipo) y cada sección aporta algo.

N/A en borrador: canonical, Open Graph, Twitter Card, velocidad, móvil,
robots, sitemap y enlaces de vuelta. En el informe: `SEO X/12`.

## 4. Factcheck

| Tier | Qué es | Uso |
|---|---|---|
| T1 | Organismos oficiales, .gob/.gov, .edu, datos primarios, documentación oficial | Preferente |
| T2 | Estudios con metodología, investigación original, artículos académicos | Sí, con nota del método |
| T3 | Prensa de referencia que enlaza la fuente original | Solo si no hay primaria |
| T4 | Blogs SEO genéricos, webs de afiliados, explicaciones sin fuente | Rechazar |
| T5 | Granjas de contenido, copias, texto IA sin rastro de fuente | Rechazar |

- **Verificar** es encontrar la cifra literal en la página y en el mismo
  contexto (país, periodo, muestra). Si es un redondeo o una paráfrasis, ajusta
  el texto al dato. Si no aparece, la página no carga o es T4/T5: quitar o
  `[VERIFICAR]`.
- **Ecos:** varias páginas que repiten un mismo dato son una sola fuente. Busca
  y cita la original.
- **Caducadas:** el año del texto tiene que ser el de la fuente (un dato de
  2024 no se vende como de 2026). En actualidad, al menos 2 fuentes de los
  últimos 30 días; en temas perennes, la edición más reciente del dato. Lo
  antiguo, solo como contexto y con su año.
- También necesitan fuente las afirmaciones no numéricas que sostienen el
  texto: normas, políticas, «el primero», «el mejor», cuestiones legales.

## 5. Schema

- Parte de `plantillas/schema.json`: BlogPosting + Person + Organization +
  BreadcrumbList.
- **FAQPage solo si hay FAQ visible**, con preguntas y respuestas literales. Es
  opcional: Google retiró los resultados enriquecidos de FAQ el 7-5-2026. Si no
  hay FAQ, borra el nodo. Nada de HowTo.
- Valores = lo visible: `headline` = title, `datePublished` = `date`,
  `dateModified` = `lastUpdated`, `wordCount` del cuerpo, `inLanguage` es-ES.
- `{siteUrl}` y `{autor}` se quedan como marcador si están PENDIENTES. Sin
  `image` si no hay imagen.
- Valídalo: `"$PY" -m json.tool schema.json > /dev/null`.

## 6. Reglas del proyecto

- Cumple las `reglas` de `proyecto.json` y la identidad (`no_suplantar`,
  `palabras_prohibidas`, `transparencia_afiliacion`).
- **Aviso de afiliación visible** si hay algún enlace de afiliado, antes del
  primero (tras los «Puntos clave» basta): «Este artículo contiene enlaces de
  afiliado: si compras a través de ellos, el autor recibe una comisión sin
  coste extra para ti».
- **Enlaces de afiliado** (los que llevan el parámetro `identidad.afiliado`) en HTML con
  `rel="sponsored"`: `<a href="URL?via=…" rel="sponsored">ancla</a>`. Solo URL
  reales (las de las ofertas: `TheCopy/proyectos/<id>/ofertas.json`), nunca
  inventadas. Los enlaces a la `identidad.landing` son normales.
- **Ninguna promesa de ingresos ni de resultados:** nada de «gana X €»,
  «garantizado» ni plazos de éxito. Resultados de otros, solo con fuente y sin
  presentarlos como lo esperable.
- Dinero y negocio son temas YMYL: prudencia y nada de asesoramiento
  financiero ni legal personalizado.
- Un solo CTA, acorde con el tema: la oferta que encaje o la `identidad.landing`.

## 7. Autor (E-E-A-T)

- Firma con nombre real; nunca «Admin» ni «Equipo». Si está PENDIENTE,
  `author: "[AUTOR PENDIENTE]"` y aviso en el informe.
- Bio de 2–3 frases al final, solo con datos reales (rol, credencial, de qué
  escribe). Si no los hay, se omite.
