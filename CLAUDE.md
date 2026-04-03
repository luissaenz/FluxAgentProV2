# 🤖 Instrucciones para Claude Code

## ⛔ CÓDIGO PROTEGIDO - NO MODIFICAR BAJO NINGUNA CIRCUNSTANCIA

Los siguientes archivos/directorios contienen código crítico de **CrewAI** y están **COMPLETAMENTE PROHIBIDOS** de modificar:

### Directorios/Archivos Bloqueados:
- `src/crews/` - Implementación de agentes CrewAI
- `src/flows/multi_crew_flow.py` - Flujos multi-agente
- `tests/unit/test_base_crew.py` - Tests de CrewAI
- `tests/integration/test_multi_crew_flow.py` - Tests de integración

### Protecciones Implementadas:
1. **Git Pre-commit Hook** - Rechaza automáticamente cualquier commit que intente modificar estos archivos
2. **Este documento CLAUDE.md** - Instrucciones explícitas para agentes
3. **Code Review Manual** - El propietario revisa todos los cambios

### Qué Hacer Si Necesito Tocar Estos Archivos:
- ❌ NO intentes modificarlos directamente
- ✅ Abre un issue describiendo el cambio necesario
- ✅ Espera aprobación explícita del propietario
- ✅ El propietario hará los cambios manualmente

---

## ✅ Código que SÍ Puedo Modificar

### API & Middleware (Permitido)
- `src/api/` - Rutas, middlewares, autenticación
- `src/api/middleware.py` - JWT, JWKS, RLS
- `src/api/routes/` - Endpoints

### Infraestructura (Permitido)
- `src/db/` - Sesiones, migraciones
- `src/config.py` - Configuración
- `src/events/` - Event store

### Flujos Internos (Permitido)
- `src/flows/base_flow.py` - Clase base de flujos
- `src/flows/registry.py` - Registro de flujos
- `src/flows/coctel_flows.py` - Implementaciones específicas de Coctel
- `src/flows/state.py` - State management

### Frontend & Scripts (Permitido)
- `dashboard/` - Código Next.js/React
- `scripts/` - Scripts de utilidad

---

## 📋 Principios de Desarrollo

1. **No toques CrewAI** - Nunca. Bajo ninguna circunstancia.
2. **Sé conservador** - Solo cambia lo necesario
3. **Documenta** - Explica el "por qué" en commits
4. **Prueba** - Ejecuta demos antes de commitear
5. **Pide ayuda** - Si no estás seguro, pregunta

---

## 🔐 Verificación

Antes de hacer commit, verifica:
```bash
git diff --cached src/crews/ src/flows/multi_crew_flow.py
```

Si hay cambios, el hook rechazará el commit automáticamente. ✓

---

## 📞 Contacto

Si necesitas modificar código protegido:
1. Abre un issue describiendo el cambio
2. Espera aprobación del propietario
3. El propietario hará el cambio manualmente

---

**Última actualización:** 2026-04-03
**Próxima revisión:** 2026-05-03
