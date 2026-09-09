"""
Normalización tipográfica del texto de la historia (regla de Sergio).

Los textos/subtítulos van en MINÚSCULAS pero se capitaliza la primera letra de la
frase y la primera letra que sigue a un signo de cierre de oración (`.` `!` `?`).
No se capitaliza tras `;` ni se toca el dígito que sigue al punto de un número
(decimales/miles tipo "3.000"): esos puntos no llevan espacio detrás, así que la
regla —que exige separador tras el signo— nunca los trata como fin de oración.
"""
from __future__ import annotations
import re

# Letras (incluye acentos y ñ/ü) que sí se capitalizan.
_LETRA = "a-záéíóúàèìòùäëïöüñ"

# 1ª letra de la cadena (tras posibles símbolos/comillas/espacios iniciales).
_RE_INICIO = re.compile(rf"^([^{_LETRA}]*)([{_LETRA}])")

# Letra que abre oración: signo de cierre .!? (con posibles comillas de cierre),
# separador (espacio/salto), posibles signos de apertura (¿ ¡ « " ' ( [) y la
# primera letra. Al exigir separador tras el signo, un punto decimal "3.000"
# (sin espacio) nunca dispara la capitalización, y ';' no está en la clase, así
# que tampoco capitaliza.
_RE_TRAS_PUNTO = re.compile(rf"([.!?]+[\"'»)\]]?\s+[¿¡«\"'(\[]*)([{_LETRA}])")


def capitalizar_frase(texto: str) -> str:
    """Aplica la regla de Sergio: todo en minúsculas salvo inicio de oración."""
    if not texto:
        return texto
    s = texto.lower()
    s = _RE_INICIO.sub(lambda m: m.group(1) + m.group(2).upper(), s, count=1)
    s = _RE_TRAS_PUNTO.sub(lambda m: m.group(1) + m.group(2).upper(), s)
    return s
