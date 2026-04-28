# Revisión Plan FAP-Bundle (Importación de Agentes)

Fecha: 2026-04-27

---

## Lo Bueno

1. **Regla fundamental sólida** — Eliminar creación ad-hoc obliga a que todo agente pase por pipeline validado. Reduce inconsistencias.

2. **Estructura ZIP pragmática** — `manifest.json` + `agents/` + `flows/` + `skills/` + `context/` cubre los componentes necesarios.

3. **Upsert inteligente** — Actualizar en lugar de duplicar por `org_id`+`role` es correcto para versionado.

4. **Hot-loading** — Sin reinicio de API es valioso para producción.

---

## Riesgos y Huecos

| Área | Problema |
|------|----------|
| **Seguridad AST** | Bloquear `os`, `subprocess` por nombre es insuficiente. `importlib`, `ctypes`, `mmap` pueden evadirlo. AST no es sandbox real — necesita `restrictedpython` o seccomp/cgroups. |
| **Rollback ambiguo** | Si falla post-extracción, ¿cómo se limpian archivos? Si hay symlinks o archivos abiertos, el delete puede fallar o corromper. |
| **Archivos huérfanos** | DB transaccional + archivos en disco no transaccional. Si DB hace commit pero persistencia de archivos falla, queda inconsistente. |
| **Sin firma digital** | El ZIP no tiene mecanismo de verificación de integridad. Cualquiera con acceso puede modificar. |
| **Dependencias Python** | Skills pueden requerir `pip install` externo. Hot-loading no resuelve eso. |
| **UI sin especificación** | "Import Wizard" no dice qué framework (React? HTMX? Streamlit?), ni cómo conecta con el endpoint. |

---

## Faltantes Críticos

1. **Schema versionado** — ¿Qué pasa cuando `manifest.json` cambia de versión? Sin migration strategy, bundles viejos rompen.

2. **Límites de tamaño** — ¿ZIP máximo? ¿N entidades por bundle? Productivamente alguien subirá un bundle de 500MB.

3. **Rate limiting / quotas** — Sin controls de cuántos bundles puede importar una org.

4. **Testing del sandbox** — Matriz B7 solo valida bloqueo de `import os`, no evade técnicas de escape.

---

## Veredicto

**Viable como dirección, incompleto para producción.**

El plan captura el "qué" pero falla en el "cómo" para seguridad y consistencia transaccional.

Para que funcione:
- Reemplazar sandbox AST con `restrictedpython` + `seccomp`
- Persistencia solo en DB (no archivos temporales en disco)
- Añadir SHA256 por archivo en manifest
- Especificar límites y quotas
