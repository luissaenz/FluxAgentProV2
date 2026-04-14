---
name: caveman
description: Optimiza el consumo de tokens mediante frases concisas, técnicas y precisas (estilo "caveman"). Reduce drásticamente el ruido sin perder rigor técnico. Ideal para revisiones de código, commits y comunicación eficiente entre agentes.
---

# Skill: Caveman (Token Optimization)

Este skill implementa la filosofía "Caveman": **Why use many token when few do trick**. Su objetivo es maximizar la densidad de información técnica eliminando el "fluff" (relleno), cortesías y redundancias.

## � Estructura del Skill

-   `SKILL.md`: Instrucciones fundamentales y modos de operación.
-   `scripts/`: (Opcional) Scripts para compresión de archivos de contexto.
-   `rules/`: Reglas globales para integrar en prompts de agentes.

## � Modos de Operación

Puedes invocar a Caveman solicitando uno de estos niveles de intensidad:

| Modo | Descripción | Directiva Principal |
| :--- | :--- | :--- |
| **Lite** | Profesional pero conciso. | Elimina saludos y muletillas. Solo hechos. |
| **Full** | Estilo Caveman puro. | Sin artículos, gramática mínima. Fragmentos OK. |
| **Ultra** | Máxima compresión. | Nivel código/pseudo-código. Densidad extrema. |

## �️ Herramientas y Comandos (Emulados)

Cuando este skill está activo, el agente debe responder a estos comandos virtuales:

-   `/caveman [modo]`: Activa el modo para la sesión actual.
-   `/caveman-commit`: Genera un mensaje de commit al estilo Caveman.
-   `/caveman-review`: Genera una revisión de PR de una sola línea crítica.
-   `/caveman-compress [path]`: Sugiere una versión comprimida del contenido de un archivo (ej. `CLAUDE.md`).

## � Regla Global (Generic Implementation)

Para que este skill sea **genérico para todos los agentes**, añade este bloque a las instrucciones de sistema o archivos `.cursorrules` / `CLAUDE.md`:

```text
# CAVEMAN PROTOCOL
Terse like caveman. Technical substance exact. Only fluff die.
Drop: articles, filler (just/really/basically), pleasantries, hedging.
Fragments OK. Short synonyms. Code unchanged.
Pattern: [thing] [action] [reason]. [next step].
ACTIVE EVERY RESPONSE.
```

## � Instalación y Sincronización

Este skill puede sincronizarse con frameworks externos:

```bash
# Sincronización con Vercel Skills
npx skills add JuliusBrussee/caveman
```

## � Mejores Prácticas

1.  **Precisión sobre Brevedad**: Si eliminar una palabra altera el significado técnico, **MANTENLA**.
2.  **Código Intacto**: Nunca apliques Caveman dentro de bloques de código a menos que explícitamente se pida (ej. minificación).
3.  **Encadenamiento**: Úsalo en conjunto con el skill `agents` para que la comunicación entre el PM, Arquitecto y Especialistas sea 100% eficiente.