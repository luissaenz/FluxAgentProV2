"""
Setup Script para la Demo CoctelPro
Obtiene JWT_TOKEN y COCTEL_PRO_ORG_ID automaticamente de Supabase
"""

import sys
import os
from pathlib import Path
import re

# Cargar .env
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("❌ Error: SUPABASE_URL y SUPABASE_ANON_KEY no están configuradas en .env")
    sys.exit(1)

try:
    from supabase import create_client
except ImportError:
    print("❌ Error: supabase-py no está instalado")
    print("   Ejecuta: uv pip install supabase")
    sys.exit(1)


def get_credentials():
    """Obtiene credenciales del usuario demo (del .env o hardcodeadas)."""
    print("\n" + "=" * 60)
    print("  SETUP DEMO COCKTELPRO - Obtener JWT y ORG_ID")
    print("=" * 60)

    # Valores por defecto (cambiar si es necesario)
    email = "admin@coctelpro.com"
    password = "1234Admin"

    # Permite override via variables de entorno
    email = os.getenv("DEMO_USER_EMAIL", email)
    password = os.getenv("DEMO_USER_PASSWORD", password)

    print(f"\n📧 Email: {email}")
    print(f"🔐 Usando credenciales guardadas")

    if not email or not password:
        print("❌ Email y contraseña son requeridos")
        sys.exit(1)

    return email, password


def get_jwt_and_org_id(email: str, password: str) -> tuple[str, str]:
    """Obtiene JWT y ORG_ID de Supabase, creando org y membership si es necesario."""
    print("\n🔄 Conectando a Supabase...")

    try:
        # Para operaciones de admin (crear org, agregar miembro) usamos service key
        sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        sb_admin = create_client(SUPABASE_URL, os.getenv("SUPABASE_SERVICE_KEY"))

        print("🔐 Autenticando usuario...")
        response = sb.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        jwt_token = response.session.access_token
        user_id = response.user.id
        print(f"✅ JWT obtenido: {jwt_token[:20]}...")
        print(f"   User ID: {user_id}")

        print("🔍 Buscando organizacion 'CoctelPro'...")
        orgs = sb_admin.table("organizations").select("id, name").eq("name", "CoctelPro").execute()

        if orgs.data:
            org_id = orgs.data[0]["id"]
            print(f"✅ Organizacion encontrada: {org_id}")
        else:
            print("📝 Creando organizacion 'CoctelPro'...")
            try:
                result = sb_admin.table("organizations").insert({
                    "name": "CoctelPro",
                    "slug": "coctel-pro"
                }).execute()
                org_id = result.data[0]["id"]
                print(f"✅ Organizacion creada: {org_id}")
            except Exception as e:
                print(f"❌ Error creando organizacion: {e}")
                sys.exit(1)

        # Verificar que el usuario sea miembro de la organizacion
        print("🔗 Verificando membresía del usuario en la organizacion...")
        try:
            # Use authenticated client to check membership (user should see their own memberships)
            membership = sb.table("org_members").select("id").eq("org_id", org_id).eq("user_id", user_id).execute()
        except Exception:
            # If authenticated check fails, try with admin client
            membership = sb_admin.table("org_members").select("id").eq("org_id", org_id).eq("user_id", user_id).execute()

        if not membership.data:
            print("📝 Agregando usuario a la organizacion...")
            try:
                sb_admin.table("org_members").insert({
                    "org_id": org_id,
                    "user_id": user_id,
                    "email": email,
                    "role": "org_owner",
                    "is_active": True
                }).execute()
                print(f"✅ Usuario agregado como org_owner")
            except Exception as e:
                print(f"❌ Error agregando usuario: {e}")
                sys.exit(1)
        else:
            print(f"✅ Usuario ya es miembro de la organizacion")

        return jwt_token, org_id

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def update_demo_script(jwt_token: str, org_id: str):
    """Actualiza demo_coctel.py con los valores obtenidos."""
    demo_path = Path(__file__).parent / "demo_coctel.py"

    if not demo_path.exists():
        print(f"❌ Archivo no encontrado: {demo_path}")
        sys.exit(1)

    print(f"\n📝 Actualizando {demo_path}...")

    with open(demo_path, "r") as f:
        content = f.read()

    # Reemplazar los valores
    content = re.sub(
        r'COCTEL_PRO_ORG_ID = "[^"]*"',
        f'COCTEL_PRO_ORG_ID = "{org_id}"',
        content
    )

    content = re.sub(
        r'JWT_TOKEN = "[^"]*"',
        f'JWT_TOKEN = "{jwt_token}"',
        content
    )

    # Actualizar tambien el header X-Org-ID para que sea consistente
    content = re.sub(
        r'"X-Org-ID": "[^"]*"',
        f'"X-Org-ID": "{org_id}"',
        content
    )

    with open(demo_path, "w") as f:
        f.write(content)

    print(f"✅ demo_coctel.py actualizado correctamente")


def main():
    email, password = get_credentials()
    jwt_token, org_id = get_jwt_and_org_id(email, password)
    update_demo_script(jwt_token, org_id)

    print("\n" + "=" * 60)
    print("  ✅ SETUP COMPLETADO!")
    print("=" * 60)
    print("\n📋 Valores configurados:")
    print(f"   JWT_TOKEN: {jwt_token[:30]}...")
    print(f"   COCTEL_PRO_ORG_ID: {org_id}")
    print("\n▶️  Ahora puedes ejecutar la demo:")
    print("   uv run python scripts/demo_coctel.py")
    print()


if __name__ == "__main__":
    main()
