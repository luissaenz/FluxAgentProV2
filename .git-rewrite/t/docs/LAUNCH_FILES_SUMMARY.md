# 📁 Archivos de Launch Creados

## Resumen

Se han creado **4 archivos principales** para facilitar el lanzamiento y desarrollo del proyecto FluxAgentProV2:

---

## 1. `launch.sh` - Script Principal de Launch

**Ubicación:** `/home/daniel/develop/Personal/FluxAgentProV2/launch.sh`

**Propósito:** Script bash completo para levantar el proyecto con validaciones automáticas.

**Características:**
- ✅ Verifica y crea entorno virtual si no existe
- ✅ Verifica archivo `.env` y variables de entorno
- ✅ Instala dependencias automáticamente
- ✅ Ejecuta tests opcionales con `--test`
- ✅ Configura parámetros del servidor (host, port, reload, workers)
- ✅ Soporta modos development y production
- ✅ Muestra endpoints disponibles y documentación

**Uso:**
```bash
# Launch normal
./launch.sh

# Launch con tests previos
./launch.sh --test
```

**Variables de Entorno Opcionales:**
```bash
HOST=0.0.0.0        # Default: 0.0.0.0
PORT=8000           # Default: 8000
RELOAD=true         # Default: true (development)
WORKERS=1           # Default: 1 (4 en production)
APP_ENV=development # development o production
```

---

## 2. `Makefile` - Comandos de Desarrollo

**Ubicación:** `/home/daniel/develop/Personal/FluxAgentProV2/Makefile`

**Propósito:** Proporcionar comandos cortos y memorables para tareas comunes.

**Comandos Disponibles:**

| Comando | Descripción |
|---------|-------------|
| `make help` | Mostrar ayuda de comandos |
| `make install` | Instalar dependencias básicas |
| `make dev` | Instalar dependencias de desarrollo |
| `make server` | Levantar servidor (development) |
| `make prod` | Levantar servidor (production) |
| `make test` | Ejecutar tests |
| `make test-verbose` | Ejecutar tests con output detallado |
| `make test-cov` | Ejecutar tests con coverage report |
| `make lint` | Ejecutar linter |
| `make clean` | Limpiar archivos temporales |
| `make migrate` | Mostrar instrucciones de migración |
| `make shell` | Abrir shell de Python en el venv |
| `make logs` | Ver logs del servidor |
| `make stop` | Detener servidor |
| `make restart` | Reiniciar servidor |
| `make check-env` | Verificar variables de entorno |
| `make setup` | Setup inicial completo |

**Variables Personalizables:**
```bash
# Cambiar puerto
make server PORT=8080

# Ejecutar tests específicos
make test test-args='tests/unit/'

# Cambiar host
make server HOST=127.0.0.1
```

**Ejemplos de Uso:**
```bash
# Setup inicial
make setup

# Levantar servidor
make server

# Ejecutar tests con coverage
make test-cov

# Limpiar y reinstalar
make clean && make dev
```

---

## 3. `docs/LAUNCH_GUIDE.md` - Guía de Launch

**Ubicación:** `/home/daniel/develop/Personal/FluxAgentProV2/docs/LAUNCH_GUIDE.md`

**Propósito:** Documentación completa en español para levantar y usar el proyecto.

**Secciones Incluidas:**
- ⚡ Quick Start (3 opciones)
- 📋 Prerrequisitos detallados
- 🎯 Comandos principales (Make, launch.sh, manuales)
- 🔍 Verificación de instalación
- 🏗️ Diagrama de arquitectura
- 📊 Fases del proyecto
- 🐛 Troubleshooting común
- 📚 Recursos adicionales

**Uso:**
```bash
# Ver en el navegador
xdg-open docs/LAUNCH_GUIDE.md

# O en terminal
cat docs/LAUNCH_GUIDE.md
```

---

## 4. `.vscode/launch.json` - Configuración VS Code

**Ubicación:** `/home/daniel/develop/Personal/FluxAgentProV2/.vscode/launch.json`

**Propósito:** Configuración de debugging para VS Code.

**Configuraciones Incluidas:**

### 4.1 `FluxAgentProV2: Launch Server`
- Lanza el servidor uvicorn con debug
- Hot reload activado
- Puerto 8000

### 4.2 `FluxAgentProV2: Run Tests`
- Ejecuta todos los tests con pytest
- Output verbose
- Incluye tests de todas las fases

### 4.3 `FluxAgentProV2: Run Specific Test`
- Ejecuta el archivo de test abierto
- Útil para debugging de tests específicos
- Variables `${file}` dinámicas

### 4.4 `FluxAgentProV2: Python Shell`
- Abre una shell interactiva de Python
- Con el entorno del proyecto cargado
- Útil para experimentación

**Uso en VS Code:**
1. Presiona `F5` o ve a Run → Start Debugging
2. Selecciona la configuración deseada
3. Para tests específicos, abre el archivo y usa "Run Specific Test"

---

## 🎯 Flujo de Trabajo Recomendado

### Primera Vez (Setup Inicial)

```bash
# 1. Clonar/navegar al proyecto
cd /home/daniel/develop/Personal/FluxAgentProV2

# 2. Setup completo
make setup

# O usar el script
./launch.sh
```

### Desarrollo Diario

```bash
# 1. Levantar servidor (Opción A: Make)
make server

# 1. Levantar servidor (Opción B: launch.sh)
./launch.sh

# 1. Levantar servidor (Opción C: VS Code)
# Presiona F5 y selecciona "FluxAgentProV2: Launch Server"
```

### Ejecutar Tests

```bash
# Tests rápidos
make test

# Tests con coverage
make test-cov

# Tests específicos
make test test-args='tests/unit/test_baseflow.py'

# Tests verbose
make test-verbose
```

### Antes de Commit

```bash
# Limpiar
make clean

# Ejecutar todos los tests
make test-verbose

# Verificar variables de entorno
make check-env
```

---

## 📊 Comparativa de Métodos

| Método | Ventajas | Cuándo Usar |
|--------|----------|-------------|
| **launch.sh** | Automático, validaciones completas | Primera vez, CI/CD |
| **Makefile** | Comandos cortos, flexible | Desarrollo diario |
| **VS Code** | Debugging integrado, breakpoints | Debugging, desarrollo |
| **Manual** | Control total, educativo | Aprendizaje, troubleshooting |

---

## 🔗 Archivos Relacionados Existentes

- `.env.example` - Template de variables de entorno
- `pyproject.toml` - Dependencias del proyecto
- `README.md` - Documentación principal
- `docs/TEST_SUMMARY_PHASES_1-4.md` - Resumen de tests

---

## ✅ Checklist de Verificación

Después de crear los archivos, verifica:

```bash
# 1. launch.sh es ejecutable
ls -la launch.sh
# Debe mostrar: -rwxr-xr-x

# 2. Makefile funciona
make help
# Debe mostrar la lista de comandos

# 3. .vscode/launch.json existe
cat .vscode/launch.json
# Debe mostrar la configuración JSON

# 4. docs/LAUNCH_GUIDE.md existe
head docs/LAUNCH_GUIDE.md
# Debe mostrar el inicio de la guía
```

---

## 🎉 ¡Todo Listo!

Los 4 archivos de launch han sido creados exitosamente:

1. ✅ `launch.sh` - Script bash automático
2. ✅ `Makefile` - Comandos de desarrollo
3. ✅ `docs/LAUNCH_GUIDE.md` - Guía completa
4. ✅ `.vscode/launch.json` - Debugging en VS Code

**Próximo paso:** Ejecuta `make setup` o `./launch.sh` para comenzar.
