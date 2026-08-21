# Pricing — viral-pipeline-v6

Desglose de costes operativos de la skill. Útil para entender dónde va cada euro antes de escalar.

> ⚠️ Precios snapshot 2026-05. Verificar siempre en la web del proveedor.
> Tipo de cambio asumido: $1 ≈ €0.93.

---

## TL;DR

- **Variable por vídeo de 30s en 1080p**: **~€1.40** (solo HeyGen)
- **Variable por lote de 3**: **~€4.20**
- **Suscripciones mínimas mensuales**: **~€5/mes** (solo ElevenLabs Starter)
- **HeyGen API**: pay-as-you-go, sin plan mensual
- **Hobbyist (12 vídeos/mes)**: **~€22/mes** total
- **Pro (270 vídeos/mes)**: **~€383/mes** total

---

## 1. HeyGen — pay-as-you-go (no hay plan mensual)

Autenticación con **API key** (`x-api-key` header) factura en el tier API contra una **billetera prepago en USD**. Sin suscripción.

> Si autenticas con OAuth bearer token factura contra el plan web del cliente. Para esta skill SIEMPRE usar API key.

Rates oficiales (snapshot mayo 2026, Avatar IV/V — Photo Avatar):

| Resolución | $/segundo | $/minuto | €/segundo* | €/minuto* |
|------------|-----------|----------|-----------|-----------|
| **720p / 1080p** | **$0.05** | $3.00 | **€0.047** | €2.79 |
| 4K | $0.0667 | $4.00 | €0.062 | €3.72 |

\* Tipo $1 ≈ €0.93

Esta skill genera 1080p por defecto. Coste por vídeo según duración:

| Duración vídeo | Coste 1080p |
|----------------|-------------|
| 15s | ~€0.70 |
| **30s (típico)** | **~€1.40** |
| 45s | ~€2.10 |
| 60s | ~€2.79 |

> Avatar III (legacy, $1/min) NO está disponible para nuevos clientes. Esta skill usa Avatar IV.

---

## 2. ElevenLabs — Starter $5/mes (incluido, no marginal)

Plan mínimo necesario: **Starter ~$5/mes ≈ €4.65/mes**. Incluye:

- Voice cloning (necesario para clonar la voz del cliente)
- Modelo `eleven_v3`
- Cuota mensual de caracteres (revisar dashboard ElevenLabs — varía por plan)

A efectos de variable por vídeo: **€0** marginal (entra en la cuota del plan).

> Si superas la cuota mensual de chars (~30k en Starter), hay que subir a Creator (~$22). A 500 chars/script son ~60 vídeos antes de tocar techo.

---

## 3. Pexels — Free

API gratuita con registro instantáneo.

---

## 4. Airtable — Free

Free tier soporta 1.000 records por base. Sobra para este caso.

---

## 5. Hosts públicos (uploads de attachments)

- `0x0.st`: gratis, retención 30d, ≤512MB
- `catbox.moe`: gratis, ≤200MB (fallback)
- **€0**

---

## 6. Total mensual por volumen (1080p, 30s/vídeo)

Suma: `subs (€5) + variable (€1.40 × N vídeos)`

| Cadencia | Vídeos/mes | Variable HeyGen | Subs | **Total/mes** |
|----------|-----------|-----------------|------|---------------|
| Hobbyist (1 lote/sem) | 12 | €16.80 | €5 | **~€22** |
| Activo (1 lote/día) | 90 | €126 | €5 | **~€131** |
| Pro (3 lotes/día) | 270 | €378 | €5* | **~€383** |
| Industrial (10 lotes/día) | 900 | €1.260 | €5-20* | **~€1.265-1.280** |

\* A partir de ~60 vídeos/mes probable upgrade ElevenLabs a Creator (~€20/mes) por cuota de chars.

---

## 7. Dónde pueden dispararse los costes

| Causa | Síntoma | Cómo lo evita la skill |
|-------|---------|------------------------|
| Re-generar HeyGen por error | €1.40 perdidos por intento | `heygen_wait` poll correcto, no relanza si ya hay video_id |
| Vídeos >30s sin querer | Variable se dispara linealmente | El agent valida longitud antes de TTS — recortar si script genera >45s |
| Subir a 4K sin necesidad | +33% coste vs 1080p | Default 1080p — NO cambiar a 4K salvo petición explícita |
| Cuota ElevenLabs Starter agotada | Bloqueo TTS a mitad de mes | Vigilar dashboard si haces >60 vídeos/mes |
| Wallet HeyGen vacía | Generación bloqueada | Mantener balance mínimo de €15-20 cargados |

---

## 8. Cómo medir tu coste real

- `pipeline_core.bump_success_counter()` lleva contador persistente en `~/.viral-pipeline/success_counter.txt`. Multiplica por **€1.40** para variable real.
- HeyGen balance: `GET /v3/users/me → wallet` (devuelve saldo prepago en USD).
- ElevenLabs: dashboard mensual para detectar si te has pasado de cuota.

---

## ¿Quieres que alguien lo lleve por ti?

Avatar Growth (Kaizen Systems) ofrece dos servicios alrededor de pipelines como este:

- **DFY (Done For You)**: nosotros llevamos research, scripting, edición e iteración por métricas. Tú solo apruebas.
- **DWY (Done With You)**: te montamos el sistema y trabajamos contigo en ciclos para que aprendas a operarlo.

En ambos casos arrancamos con una **llamada de descubrimiento** para entender tu caso y proponer la opción que más sentido tenga. Sin precio fijo público — depende del scope.

→ [Reservar llamada de descubrimiento](https://bit.ly/3RAAftB)
