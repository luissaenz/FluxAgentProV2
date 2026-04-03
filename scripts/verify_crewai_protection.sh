#!/bin/bash
# Verificar que los archivos de CrewAI no han sido modificados

CREWAI_FILES=(
    "src/crews/base_crew.py"
    "src/crews/generic_crew.py"
    "src/flows/multi_crew_flow.py"
    "tests/unit/test_base_crew.py"
    "tests/integration/test_multi_crew_flow.py"
)

echo "🔒 Verificando integridad de archivos de CrewAI"
echo "=============================================="
echo ""

VIOLATIONS=0

for file in "${CREWAI_FILES[@]}"; do
    if [ -f "$file" ]; then
        # Verificar si hay cambios sin commitear
        if git diff "$file" | grep -q .; then
            echo "❌ $file: Tiene cambios no guardados"
            VIOLATIONS=$((VIOLATIONS + 1))
        else
            echo "✅ $file: Sin cambios"
        fi
    else
        echo "⚠️  $file: Archivo no encontrado"
    fi
done

echo ""
if [ $VIOLATIONS -eq 0 ]; then
    echo "✅ Archivos de CrewAI protegidos correctamente"
    exit 0
else
    echo "❌ Se encontraron violaciones de protección"
    exit 1
fi
