# 🛡️ REGLAS DE SEGURIDAD PARA BUNDLES (FAP-IMPLEMENTOR)

Todas las habilidades (skills) generadas para FluxAgentPro deben cumplir estrictamente con estas reglas de seguridad. El incumplimiento de estas reglas resultará en el bloqueo de la ejecución por parte del `SecurityGuard`.

## 1. Módulos Permitidos (Allowlist)
Solo podés importar los siguientes módulos. Cualquier otro módulo no incluido aquí está prohibido.

- `crewai`
- `pydantic`
- `json`
- `re`
- `datetime`
- `math`
- `random`
- `typing`
- `abc`
- `uuid`
- `logging`
- `time`
- `collections`
- `functools`
- `itertools`
- `pydantic_core`
- `annotated_types`

## 2. Módulos Prohibidos (Blacklist Crítica)
Bajo ninguna circunstancia debés generar código que importe o use:

- **Sistema**: `os`, `subprocess`, `shutil`, `sys`
- **Red**: `socket`, `urllib`, `http`, `requests`, `httpx`, `aiohttp`, `urllib3`
- **Dinámicos/Introspección**: `importlib`, `inspect`, `gc`, `ctypes`, `mmap`

## 3. Funciones Prohibidas
No podés usar las siguientes funciones incorporadas de Python:

- `eval()`
- `exec()`
- `compile()`
- `open()` (Para lectura/escritura de archivos)
- `__import__()`

## 4. Acceso a Atributos
- Está prohibido el acceso a atributos que comiencen con doble guion bajo (`__`), como `__subclasses__`, `__globals__`, etc., para evitar escapes del sandbox.

## 5. Desarrollo de Herramientas (Tools) y Secretos
Para crear herramientas (`Tools`) que interactúen con APIs externas o requieran autenticación:
- Es **estrictamente obligatorio** heredar de `OrgBaseTool` (importado desde `src.tools.base_tool`). Queda prohibido el uso directo de `BaseTool` de crewai.
- Los secretos (tokens, passwords, API keys) NUNCA deben exponerse en el código ni ser retornados al LLM.
- Se debe utilizar exclusivamente el método `self._get_secret("nombre_secreto")` para recuperar credenciales internamente dentro del método `_run()` de la herramienta. El LLM solo debe recibir el *resultado* de la operación, nunca el secreto en sí.

## 6. Recomendación para Funcionalidad Externa
Si necesitás interactuar con el mundo exterior (archivos, APIs, base de datos), **NO** intentes hacerlo directamente en la skill. En su lugar:
1.  Utilizá el **Model Context Protocol (MCP)** si está disponible.
2.  Delegá la tarea a un Agente que tenga las herramientas necesarias (construidas sobre `OrgBaseTool`).
3.  Utilizá las interfaces de persistencia proporcionadas por el framework de FAP si están disponibles en el contexto.

---
**Nota**: Estas reglas son verificadas mediante análisis estático (AST) y en tiempo de ejecución (RestrictedPython).
