"""
validate_builder_nav.py
========================
Valida 4 puntos críticos de la integración del Builder en el Dashboard:
  1. SSOT sidebar: app-sidebar.tsx no tiene código muerto (array navMain), NavMain recibe items={defaultNavItems}
  2. Archivos Next.js: loading.tsx y error.tsx existen en app/(app)/builder/
  3. Error Boundary: BuilderErrorBoundary existe en components/builder/ y BuilderLayout lo usa
  4. Breadcrumb: BuilderBreadcrumb existe en components/builder/ y page.tsx lo importa

Uso:
    uv run python scripts/validate_builder_nav.py
    o desde cualquier ubicación en el proyecto.
"""

import pathlib
import re
import sys

from rich import print as rprint
from rich.console import Console
from rich.table import Table

console = Console()

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"

SIDEBAR_FILE = DASHBOARD_DIR / "components" / "app-sidebar.tsx"
NAV_MAIN_FILE = DASHBOARD_DIR / "components" / "nav-main.tsx"
BUILDER_DIR = DASHBOARD_DIR / "app" / "(app)" / "builder"
LOADING_FILE = BUILDER_DIR / "loading.tsx"
ERROR_FILE = BUILDER_DIR / "error.tsx"
BUILDER_BOUNDARY_FILE = (
    DASHBOARD_DIR / "components" / "builder" / "BuilderErrorBoundary.tsx"
)
BUILDER_LAYOUT_FILE = DASHBOARD_DIR / "components" / "builder" / "BuilderLayout.tsx"
BUILDER_BREADCRUMB_FILE = (
    DASHBOARD_DIR / "components" / "builder" / "BuilderBreadcrumb.tsx"
)
BUILDER_CANVAS_FILE = (
    DASHBOARD_DIR / "components" / "builder" / "BuilderCanvas.tsx"
)
BUILDER_PAGE_FILE = BUILDER_DIR / "page.tsx"

CHECKS: list[tuple[str, bool]] = []


def check(name: str, passed: bool) -> None:
    CHECKS.append((name, passed))


# ── 1. SSOT Sidebar ────────────────────────────────────────────────────────────
def check_sidebar_ssot() -> None:
    if not SIDEBAR_FILE.exists():
        check("app-sidebar.tsx existe", False)
        return
    content = SIDEBAR_FILE.read_text(encoding="utf-8")

    # A) No debe haber un array navMain local (dead code)
    has_navmain = bool(re.search(r"const\s+navMain\s*=\s*\[", content))
    check(
        "No hay array navMain local en app-sidebar.tsx (dead code eliminado)",
        not has_navmain,
    )

    # B) NavMain debe usarse correctamente: items={defaultNavItems} explicito
    # o sin props confiando en el fallback items ?? defaultNavItems de nav-main.tsx
    uses_navmain_explicit = bool(re.search(r'items\s*=\s*\{\s*defaultNavItems\s*\}', content))
    uses_navmain_bare = bool(re.search(r'<NavMain\b', content))
    nav_has_fallback = False
    if NAV_MAIN_FILE.exists():
        nav_content = NAV_MAIN_FILE.read_text(encoding="utf-8")
        nav_has_fallback = "items ?? defaultNavItems" in nav_content or "items || defaultNavItems" in nav_content
    navmain_ok = uses_navmain_explicit or (uses_navmain_bare and nav_has_fallback)
    check(
        "NavMain en app-sidebar.tsx recibe items={defaultNavItems} o usa fallback interno defaultNavItems",
        navmain_ok,
    )

    # C) defaultNavItems debe existir en nav-main.tsx
    if NAV_MAIN_FILE.exists():
        nav_content = NAV_MAIN_FILE.read_text(encoding="utf-8")
        has_default = "defaultNavItems" in nav_content
        has_builder_entry = "Builder" in nav_content and "/builder" in nav_content
        check("nav-main.tsx exporta defaultNavItems", has_default)
        check(
            "nav-main.tsx incluye entrada 'Builder' en defaultNavItems",
            has_builder_entry,
        )
    else:
        check("nav-main.tsx existe", False)
        check("nav-main.tsx exporta defaultNavItems — NAV_MAIN no existe", False)
        check(
            "nav-main.tsx incluye entrada 'Builder' en defaultNavItems — NAV_MAIN no existe",
            False,
        )


# ── 2. Archivos Next.js loading + error ──────────────────────────────────────
def check_nextjs_files() -> None:
    check("loading.tsx existe en app/(app)/builder/", LOADING_FILE.exists())
    check("error.tsx existe en app/(app)/builder/", ERROR_FILE.exists())


# ── 3. BuilderErrorBoundary ─────────────────────────────────────────────────────
def check_error_boundary() -> None:
    if not BUILDER_BOUNDARY_FILE.exists():
        check("BuilderErrorBoundary.tsx existe en components/builder/", False)
        check(
            "BuilderLayout envuelve el canvas en BuilderErrorBoundary — Boundary falta",
            False,
        )
        return

    check("BuilderErrorBoundary.tsx existe en components/builder/", True)

    if not BUILDER_LAYOUT_FILE.exists():
        check("BuilderLayout.tsx existe", False)
        check(
            "BuilderLayout envuelve el canvas en BuilderErrorBoundary — BuilderLayout falta",
            False,
        )
        return

    layout_content = BUILDER_LAYOUT_FILE.read_text(encoding="utf-8")
    uses_boundary = "BuilderErrorBoundary" in layout_content
    check(
        f"BuilderLayout envuelve el canvas en BuilderErrorBoundary — {'PASO' if uses_boundary else 'FALTA revisar'}",
        uses_boundary,
    )


# ── 4. Breadcrumb ──────────────────────────────────────────────────────────────
def check_breadcrumb() -> None:
    if not BUILDER_BREADCRUMB_FILE.exists():
        check("BuilderBreadcrumb.tsx existe en components/builder/", False)
        check(
            "page.tsx o BuilderLayout usa BuilderBreadcrumb — Breadcrumb falta", False
        )
        return

    check("BuilderBreadcrumb.tsx existe en components/builder/", True)

    # Buscar uso en page.tsx o BuilderLayout
    page_uses = False
    layout_uses = False

    if BUILDER_PAGE_FILE.exists():
        page_content = BUILDER_PAGE_FILE.read_text(encoding="utf-8")
        page_uses = "BuilderBreadcrumb" in page_content

    if BUILDER_LAYOUT_FILE.exists():
        layout_content = BUILDER_LAYOUT_FILE.read_text(encoding="utf-8")
        layout_uses = "BuilderBreadcrumb" in layout_content

    check(
        f"BuilderBreadcrumb integrado en page.tsx — {'PASO' if page_uses else 'NO integrado en page.tsx'}",
        page_uses or layout_uses,
    )


# ── 5. SSR ssr:false en Canvas ReactFlow ──────────────────────────────────────
# NOTA: analisis-FINAL D3 decia buscar CrewCanvas en BuilderLayout.tsx pero
# el codigo real tiene BuilderCanvas.tsx como wrapper con dynamic import
# interno de CrewCanvas con ssr:false. Ajustado al patron real.
def check_ssr_false() -> None:
    if not BUILDER_LAYOUT_FILE.exists():
        check(
            "Canvas ReactFlow cargado dinamicamente con ssr: false — SKIP BuilderLayout no encontrado",
            False,
        )
        return

    layout_content = BUILDER_LAYOUT_FILE.read_text(encoding="utf-8")
    uses_builder_canvas = "BuilderCanvas" in layout_content

    if not uses_builder_canvas:
        check(
            "Canvas ReactFlow cargado dinamicamente con ssr: false — BuilderCanvas no usado en layout",
            False,
        )
        return

    if not BUILDER_CANVAS_FILE.exists():
        check(
            "Canvas ReactFlow cargado dinamicamente con ssr: false — BuilderCanvas.tsx no encontrado",
            False,
        )
        return

    canvas_content = BUILDER_CANVAS_FILE.read_text(encoding="utf-8")
    has_ssr_false = "ssr: false" in canvas_content
    has_dynamic_import = "dynamic(" in canvas_content

    ssr_ok = has_ssr_false and has_dynamic_import
    check(
        "Canvas ReactFlow cargado dinamicamente con ssr: false (BuilderCanvas.tsx -> CrewCanvas)",
        ssr_ok,
    )


# ── Ejecución ──────────────────────────────────────────────────────────────────
def main() -> int:
    rprint(
        "\n[bold cyan]══ validate_builder_nav.py — Builder Integrity Check ══[/bold cyan]\n"
    )

    check_sidebar_ssot()
    check_nextjs_files()
    check_error_boundary()
    check_breadcrumb()
    check_ssr_false()

    # ── Tabla de resultados ──
    table = Table(title="Resultados de Validación", show_lines=True)
    table.add_column("Check", style="cyan", no_wrap=False)
    table.add_column("Estado", style="white", width=6)

    passed = 0
    failed = 0

    for name, ok in CHECKS:
        status_str = "[green]✔ OK[/green]" if ok else "[red]✘ FAIL[/red]"
        table.add_row(name, status_str)
        if ok:
            passed += 1
        else:
            failed += 1

    console.print(table)

    # ── Resumen ──
    total = passed + failed
    rprint(
        f"\n[bold]Resumen:[/bold] {passed}/{total} checks pasaron, {failed} fallaron"
    )

    if failed == 0:
        rprint(
            "[bold green]✔ Todos los checks pasaron. La estructura del Builder está correcta.[/bold green]\n"
        )
        return 0
    else:
        rprint(
            "[bold red]✘ Hay checks fallidos. Revisar antes de hacer build en producción.[/bold red]\n"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
