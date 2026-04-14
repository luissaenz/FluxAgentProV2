PASO 1

Tarea 1.0.0.2: Crear endpoint POST /api/mcp/generate-pin que:

Recibe auth del admin (middleware existente)
Llama a la lógica de secure-pin.ts existente
Retorna el PIN al admin
Vincula el PIN al org_id del admin

