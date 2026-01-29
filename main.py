"""
Code Audit Agent - Detecta errores de indices fuera de rango y null references.

Modos de uso:
  python main.py                    # Menu interactivo (o usa config.json si existe)
  python main.py --interactive      # Forzar menu interactivo
  python main.py --path ./src ...   # Modo CLI con flags (uso avanzado)
"""

import argparse
import json
import os
import subprocess
import sys

from scanner import scan_directory
from analyzer import analyze_findings
from reporter import generate_report


CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

PROVIDER_DEFAULTS = {
    "ollama": {
        "model": "ollama/deepcoder:14b",
        "api_base": "http://localhost:11434",
    },
    "openai": {
        "model": "gpt-4o",
        "api_base": None,
    },
    "anthropic": {
        "model": "claude-sonnet-4-20250514",
        "api_base": None,
    },
    "custom": {
        "model": None,
        "api_base": None,
    },
}

OLLAMA_SUGGESTED_MODELS = [
    ("deepcoder:14b", "14B params - Nivel O3-mini, excelente para codigo"),
    ("deepseek-r1:14b", "14B params - Gran razonamiento, analiza bugs muy bien"),
    ("qwen2.5-coder:14b", "14B params - Muy solido para codigo"),
    ("deepseek-coder-v2:16b", "16B params - Bueno, MoE architecture"),
    ("codellama:7b", "7B params - Liviano, rapido, aceptable"),
    ("deepcoder:1.5b", "1.5B params - Ultra liviano para PCs con poca RAM"),
]


# ─── Utilidades de consola ────────────────────────────────────────────

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_header(title):
    width = 60
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)
    print()


def print_option(num, label, description=""):
    prefix = f"  [{num}] {label}"
    if description:
        print(f"{prefix}")
        print(f"      {description}")
    else:
        print(prefix)


def ask_choice(prompt, max_val, default=None):
    """Pide al usuario que elija un numero."""
    while True:
        default_hint = f" (default: {default})" if default else ""
        raw = input(f"\n  {prompt}{default_hint}: ").strip()
        if raw == "" and default is not None:
            return default
        try:
            val = int(raw)
            if 1 <= val <= max_val:
                return val
        except ValueError:
            pass
        print(f"  Por favor ingresa un numero entre 1 y {max_val}")


def ask_text(prompt, default=None):
    """Pide texto al usuario."""
    default_hint = f" (default: {default})" if default else ""
    raw = input(f"  {prompt}{default_hint}: ").strip()
    return raw if raw else default


def ask_yes_no(prompt, default=True):
    """Pregunta si/no."""
    hint = "S/n" if default else "s/N"
    raw = input(f"  {prompt} [{hint}]: ").strip().lower()
    if raw == "":
        return default
    return raw in ("s", "si", "y", "yes")


# ─── Deteccion de Ollama ─────────────────────────────────────────────

def detect_ollama_models():
    """Detecta modelos instalados en Ollama."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return []

        models = []
        for line in result.stdout.strip().split("\n")[1:]:  # skip header
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def is_ollama_running():
    """Verifica si Ollama esta corriendo."""
    try:
        import urllib.request
        req = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        return req.status == 200
    except Exception:
        return False


# ─── Config file ─────────────────────────────────────────────────────

def load_config():
    """Carga configuracion desde config.json."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def save_config(config):
    """Guarda configuracion en config.json."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"\n  Configuracion guardada en: {CONFIG_FILE}")


def show_config(config):
    """Muestra la configuracion actual."""
    print(f"  Directorio:   {config['path']}")
    print(f"  Provider:     {config['provider']}")
    print(f"  Modelo:       {config['model']}")
    print(f"  Extensiones:  {', '.join(config['extensions'])}")
    print(f"  Output:       {config.get('output', 'REPORTE_AUDITORIA.md (en directorio analizado)')}")
    if config.get("api_base"):
        print(f"  API Base:     {config['api_base']}")


# ─── Menu interactivo ────────────────────────────────────────────────

def interactive_menu():
    """Menu interactivo paso a paso."""
    clear_screen()
    print_header("CODE AUDIT AGENT - Configuracion")
    print("  Bienvenido! Vamos a configurar el analisis paso a paso.\n")

    # ─── Paso 1: Directorio ───
    print("  --- PASO 1: Directorio a analizar ---\n")

    # Intentar detectar directorios comunes
    agent_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(agent_dir, "..", ".."))
    suggested_dirs = []

    if os.path.isdir(repo_root):
        suggested_dirs.append(repo_root)
        for item in sorted(os.listdir(repo_root)):
            full = os.path.join(repo_root, item)
            if os.path.isdir(full) and not item.startswith(".") and item not in ("tools", "packages", "node_modules"):
                if any(f.endswith(".cs") or f.endswith(".js") for _, _, files in os.walk(full) for f in files[:5]):
                    suggested_dirs.append(full)
                    if len(suggested_dirs) >= 6:
                        break

    if suggested_dirs:
        print("  Directorios detectados:\n")
        for i, d in enumerate(suggested_dirs, 1):
            name = os.path.basename(d) or d
            label = f"{name}/" if d != suggested_dirs[0] else f"{name}/ (repositorio completo)"
            print_option(i, label)
        print_option(len(suggested_dirs) + 1, "Escribir otra ruta...")

        choice = ask_choice("Elige directorio", len(suggested_dirs) + 1, default=1)
        if choice <= len(suggested_dirs):
            scan_path = suggested_dirs[choice - 1]
        else:
            scan_path = ask_text("Ruta completa del directorio")
    else:
        scan_path = ask_text("Ruta del directorio a analizar")

    scan_path = os.path.abspath(scan_path)
    if not os.path.isdir(scan_path):
        print(f"\n  Error: No existe el directorio: {scan_path}")
        sys.exit(1)

    print(f"\n  Directorio seleccionado: {scan_path}")

    # ─── Paso 2: Provider ───
    print(f"\n  --- PASO 2: Seleccionar LLM ---\n")

    print_option(1, "Ollama (local, gratis)", "Requiere Ollama instalado. Los modelos corren en tu PC.")
    print_option(2, "OpenAI (cloud, pago)", "Requiere OPENAI_API_KEY. Usa GPT-4o, etc.")
    print_option(3, "Anthropic (cloud, pago)", "Requiere ANTHROPIC_API_KEY. Usa Claude.")
    print_option(4, "Sin LLM (solo scanner)", "Detecta patrones sin analisis inteligente. Rapido, sin dependencias.")

    provider_choice = ask_choice("Elige provider", 4, default=1)
    provider_map = {1: "ollama", 2: "openai", 3: "anthropic", 4: "none"}
    provider = provider_map[provider_choice]

    model = None
    api_base = None
    no_llm = provider == "none"

    if not no_llm:
        # ─── Paso 3: Modelo ───
        print(f"\n  --- PASO 3: Seleccionar modelo ---\n")

        if provider == "ollama":
            api_base = "http://localhost:11434"

            # Detectar modelos instalados
            installed = detect_ollama_models()
            if installed:
                print("  Modelos instalados en tu Ollama:\n")
                for i, m in enumerate(installed, 1):
                    print_option(i, m)
                print_option(len(installed) + 1, "Ver modelos recomendados...")

                choice = ask_choice("Elige modelo", len(installed) + 1, default=1)
                if choice <= len(installed):
                    model = f"ollama/{installed[choice - 1]}"
                else:
                    choice = None  # fall through to suggested
            else:
                print("  No se detectaron modelos instalados en Ollama.")
                running = is_ollama_running()
                if not running:
                    print("  Ollama no parece estar corriendo.")
                    print("  Asegurate de que Ollama este instalado y corriendo.\n")
                choice = None

            if model is None:
                print("\n  Modelos recomendados para instalar:\n")
                for i, (name, desc) in enumerate(OLLAMA_SUGGESTED_MODELS, 1):
                    print_option(i, name, desc)

                choice = ask_choice("Elige modelo", len(OLLAMA_SUGGESTED_MODELS), default=1)
                selected = OLLAMA_SUGGESTED_MODELS[choice - 1][0]
                model = f"ollama/{selected}"

                # Ofrecer descargar
                if ask_yes_no(f"Descargar '{selected}' ahora?", default=True):
                    print(f"\n  Descargando {selected}... (esto puede tardar)\n")
                    subprocess.run(["ollama", "pull", selected])

        elif provider == "openai":
            print_option(1, "gpt-4o", "El mas capaz, mejor analisis")
            print_option(2, "gpt-4o-mini", "Mas rapido y barato, buen analisis")
            print_option(3, "Escribir otro modelo...")

            choice = ask_choice("Elige modelo", 3, default=1)
            if choice == 1:
                model = "gpt-4o"
            elif choice == 2:
                model = "gpt-4o-mini"
            else:
                model = ask_text("Nombre del modelo OpenAI")

            # Verificar API key
            if not os.environ.get("OPENAI_API_KEY"):
                print("\n  OPENAI_API_KEY no esta definida.")
                key = ask_text("Ingresa tu API key de OpenAI")
                if key:
                    os.environ["OPENAI_API_KEY"] = key

        elif provider == "anthropic":
            print_option(1, "claude-sonnet-4-20250514", "Rapido y capaz")
            print_option(2, "claude-opus-4-20250514", "El mas potente")
            print_option(3, "Escribir otro modelo...")

            choice = ask_choice("Elige modelo", 3, default=1)
            if choice == 1:
                model = "claude-sonnet-4-20250514"
            elif choice == 2:
                model = "claude-opus-4-20250514"
            else:
                model = ask_text("Nombre del modelo Anthropic")

            if not os.environ.get("ANTHROPIC_API_KEY"):
                print("\n  ANTHROPIC_API_KEY no esta definida.")
                key = ask_text("Ingresa tu API key de Anthropic")
                if key:
                    os.environ["ANTHROPIC_API_KEY"] = key

    # ─── Paso 4: Extensiones ───
    print(f"\n  --- PASO {'3' if no_llm else '4'}: Extensiones de archivo ---\n")

    print_option(1, ".cs .js .html .cshtml", "Todas (recomendado)")
    print_option(2, ".cs", "Solo C#")
    print_option(3, ".js .html .cshtml", "Solo frontend")
    print_option(4, "Personalizar...")

    ext_choice = ask_choice("Elige extensiones", 4, default=1)
    extensions_map = {
        1: [".cs", ".js", ".html", ".cshtml"],
        2: [".cs"],
        3: [".js", ".html", ".cshtml"],
    }
    if ext_choice in extensions_map:
        extensions = extensions_map[ext_choice]
    else:
        raw = ask_text("Extensiones separadas por espacio (ej: .cs .py .java)")
        extensions = raw.split()

    # ─── Paso 5: Output ───
    default_output = os.path.join(scan_path, "REPORTE_AUDITORIA.md")
    output_path = default_output  # simplificar, usar default

    # ─── Resumen ───
    config = {
        "path": scan_path,
        "provider": provider,
        "model": model,
        "api_base": api_base,
        "extensions": extensions,
        "output": output_path,
        "no_llm": no_llm,
    }

    print_header("RESUMEN DE CONFIGURACION")
    show_config(config)

    if ask_yes_no("\n  Guardar esta configuracion para futuras ejecuciones?", default=True):
        save_config(config)

    if not ask_yes_no("\n  Ejecutar analisis ahora?", default=True):
        print("\n  Cancelado. Ejecuta 'python main.py' para usar la config guardada.")
        sys.exit(0)

    return config


# ─── CLI con flags (modo avanzado) ───────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Code Audit Agent - Detecta errores de indices y null references",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py                                      # Menu interactivo
  python main.py --interactive                        # Forzar menu interactivo
  python main.py --path ./src --provider ollama       # CLI directo
  python main.py --path ./src --no-llm                # Solo scanner
        """,
    )
    parser.add_argument("--path", "-p", default=None, help="Ruta al directorio a analizar")
    parser.add_argument("--provider", choices=["ollama", "openai", "anthropic", "custom"], default=None)
    parser.add_argument("--model", "-m", default=None, help="Modelo LLM a usar")
    parser.add_argument("--api-base", default=None, help="URL base de la API")
    parser.add_argument("--output", "-o", default=None, help="Ruta del reporte markdown de salida")
    parser.add_argument("--extensions", "-e", nargs="+", default=None, help="Extensiones a escanear")
    parser.add_argument("--no-llm", action="store_true", help="Solo scanner, sin LLM")
    parser.add_argument("--interactive", "-i", action="store_true", help="Forzar menu interactivo")
    return parser.parse_args()


def resolve_model_from_config(config):
    """Resuelve modelo y api_base desde un dict de configuracion."""
    provider = config.get("provider", "ollama")
    model = config.get("model")
    api_base = config.get("api_base")

    if model and "/" in model:
        return model, api_base

    if model is None:
        defaults = PROVIDER_DEFAULTS.get(provider, {})
        model = defaults.get("model")

    if api_base is None:
        defaults = PROVIDER_DEFAULTS.get(provider, {})
        api_base = defaults.get("api_base")

    if provider == "ollama" and model and not model.startswith("ollama/"):
        model = f"ollama/{model}"

    return model, api_base


# ─── Ejecucion principal ─────────────────────────────────────────────

def run_audit(config):
    """Ejecuta el analisis con la configuracion dada."""
    scan_path = os.path.abspath(config["path"])
    extensions = config.get("extensions", [".cs", ".js", ".html", ".cshtml"])
    output_path = config.get("output") or os.path.join(scan_path, "REPORTE_AUDITORIA.md")
    no_llm = config.get("no_llm", False)

    print_header("CODE AUDIT AGENT")
    print(f"  Directorio:  {scan_path}")
    print(f"  Extensiones: {extensions}")
    if not no_llm:
        print(f"  Provider:    {config.get('provider', 'ollama')}")
        print(f"  Modelo:      {config.get('model', 'auto')}")

    # Paso 1: Escanear
    print_header("PASO 1: ESCANEANDO CODIGO")
    findings = scan_directory(scan_path, extensions)

    if not findings:
        print("  No se encontraron hallazgos. El codigo parece seguro.")
        return

    # Paso 2: Analizar con LLM
    if not no_llm:
        model, api_base = resolve_model_from_config(config)
        print_header("PASO 2: ANALIZANDO CON LLM")
        print(f"  Modelo: {model}")
        if api_base:
            print(f"  API Base: {api_base}")
        print(f"  Hallazgos a analizar: {len(findings)}\n")

        findings = analyze_findings(findings, model, api_base)
        model_used = model
    else:
        print("\n  [Info] Modo sin LLM: omitiendo analisis inteligente")
        for f in findings:
            f.severity = "NEEDS_REVIEW"
            f.analysis = f"Patron detectado: {f.pattern_name}. Requiere revision manual."
        model_used = "ninguno (solo scanner)"

    # Paso 3: Generar reporte
    print_header("PASO 3: GENERANDO REPORTE")
    generate_report(findings, output_path, scan_path, model_used)

    print_header("COMPLETADO")
    print(f"  Reporte generado: {output_path}\n")


def main():
    args = parse_args()

    # Caso 1: Forzar interactivo
    if args.interactive:
        config = interactive_menu()
        run_audit(config)
        return

    # Caso 2: CLI con --path (modo avanzado)
    if args.path:
        config = {
            "path": args.path,
            "provider": args.provider or "ollama",
            "model": args.model,
            "api_base": args.api_base,
            "extensions": args.extensions or [".cs", ".js", ".html", ".cshtml"],
            "output": args.output,
            "no_llm": args.no_llm,
        }
        run_audit(config)
        return

    # Caso 3: Sin argumentos → intentar config.json, si no → interactivo
    saved = load_config()
    if saved:
        print_header("CODE AUDIT AGENT")
        print("  Se encontro configuracion guardada:\n")
        show_config(saved)

        print()
        print_option(1, "Ejecutar con esta configuracion")
        print_option(2, "Configurar de nuevo (menu interactivo)")
        print_option(3, "Salir")

        choice = ask_choice("Que deseas hacer?", 3, default=1)

        if choice == 1:
            run_audit(saved)
        elif choice == 2:
            config = interactive_menu()
            run_audit(config)
        else:
            print("\n  Hasta luego!")
    else:
        config = interactive_menu()
        run_audit(config)


if __name__ == "__main__":
    main()
