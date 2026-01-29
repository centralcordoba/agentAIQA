"""
scanner.py - Escanea archivos de código buscando patrones peligrosos
de acceso a índices sin validación de bounds.
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class Finding:
    """Representa un hallazgo de código potencialmente peligroso."""
    file_path: str
    line_number: int
    line_content: str
    pattern_name: str
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)
    severity: str = ""
    analysis: str = ""
    suggested_fix: str = ""


# Patrones de búsqueda con sus descripciones
PATTERNS = [
    {
        "name": "hardcoded_index_access",
        "description": "Acceso a índice hardcodeado en colección sin verificación de bounds",
        "regex": r'\[\s*(\d+)\s*\]\s*\.',
        "min_index": 0,
        "extensions": [".cs"],
    },
    {
        "name": "split_with_index",
        "description": "Resultado de Split() accedido por índice sin verificar longitud",
        "regex": r'\.Split\([^)]+\)\s*\[\s*(\d+)\s*\]',
        "min_index": 1,
        "extensions": [".cs"],
    },
    {
        "name": "first_or_default_deref",
        "description": "FirstOrDefault() usado sin verificar null antes de acceder a propiedades",
        "regex": r'\.FirstOrDefault\(\)\s*\.\s*\w+',
        "min_index": None,
        "extensions": [".cs"],
    },
    {
        "name": "tolist_with_index",
        "description": "ToList() o ToArray() seguido de acceso por índice hardcodeado",
        "regex": r'\.To(?:List|Array)\(\)\s*\[\s*(\d+)\s*\]',
        "min_index": 0,
        "extensions": [".cs"],
    },
    {
        "name": "collection_index_zero_no_check",
        "description": "Acceso a [0] en colección que puede estar vacía",
        "regex": r'(?:list|items|result|data|contracts?|corporations?|members?|models?|urls?)\w*\s*\[\s*0\s*\]',
        "min_index": None,
        "extensions": [".cs"],
        "case_insensitive": True,
    },
    {
        "name": "js_queryselector_index",
        "description": "querySelectorAll seguido de acceso por índice sin verificar length",
        "regex": r'querySelectorAll\([^)]+\)\s*\[\s*(\d+)\s*\]',
        "min_index": 0,
        "extensions": [".html", ".js", ".ts", ".tsx", ".cshtml"],
    },
    {
        "name": "tables_index_access",
        "description": "DataSet.Tables[N] sin verificar que el DataSet tenga tablas",
        "regex": r'\.Tables\s*\[\s*(\d+)\s*\]',
        "min_index": 0,
        "extensions": [".cs"],
    },
    {
        "name": "rows_index_access",
        "description": "DataTable.Rows[N] sin verificar que tenga filas",
        "regex": r'\.Rows\s*\[\s*(\d+)\s*\]',
        "min_index": 0,
        "extensions": [".cs"],
    },
    # ─── NULL REFERENCE PATTERNS ────────────────────────────────────
    {
        "name": "parse_without_tryparse",
        "description": "int.Parse, decimal.Parse, DateTime.Parse en datos externos sin TryParse",
        "regex": r'(?:int|decimal|float|double|DateTime|long|short|byte)\.Parse\s*\(',
        "min_index": None,
        "extensions": [".cs"],
    },
    {
        "name": "tostring_on_nullable",
        "description": ".ToString() en valor que puede ser null (campo de DB, SharePoint, dictionary)",
        "regex": r'(?:oListItem|row|reader|item|field|value)\s*\[["\w]+\]\s*\.ToString\(\)',
        "min_index": None,
        "extensions": [".cs"],
        "case_insensitive": True,
    },
    {
        "name": "first_single_no_check",
        "description": ".First() o .Single() que crashean si la coleccion esta vacia (usar FirstOrDefault)",
        "regex": r'\.(?:First|Single|Last)\(\)\s*[;.]',
        "min_index": None,
        "extensions": [".cs"],
    },
    {
        "name": "cast_without_as_or_is",
        "description": "Cast directo (Type)variable que crashea si el tipo no coincide",
        "regex": r'\(\s*(?:FieldLookupValue|FieldUrlValue|int|string|decimal|DateTime)\s*\)\s*\w+\s*\[',
        "min_index": None,
        "extensions": [".cs"],
    },
    {
        "name": "appsettings_direct_access",
        "description": "ConfigurationManager.AppSettings[key] usado directo sin verificar null",
        "regex": r'AppSettings\s*\[\s*"[^"]+"\s*\]\s*\.(?:ToString|Split|Trim|ToLower|ToUpper)',
        "min_index": None,
        "extensions": [".cs"],
    },
    # ─── JAVASCRIPT / TYPESCRIPT / HTML CRASH PATTERNS ──────────────
    {
        "name": "js_getelementbyid_direct",
        "description": "document.getElementById().value/style sin verificar que el elemento exista",
        "regex": r'getElementById\s*\([^)]+\)\s*\.(?:value|style|innerHTML|textContent|classList|src|href)',
        "min_index": None,
        "extensions": [".html", ".js", ".ts", ".tsx", ".cshtml"],
    },
    {
        "name": "js_json_parse_no_try",
        "description": "JSON.parse() sin try-catch que crashea con string invalido",
        "regex": r'JSON\.parse\s*\(',
        "min_index": None,
        "extensions": [".html", ".js", ".ts", ".tsx", ".cshtml"],
    },
    {
        "name": "razor_model_direct",
        "description": "@Model.Property sin verificar null en Razor view",
        "regex": r'@Model\.\w+',
        "min_index": None,
        "extensions": [".cshtml"],
    },
    # ─── TYPESCRIPT SPECIFIC PATTERNS ──────────────────────────────
    {
        "name": "ts_non_null_assertion",
        "description": "Uso de ! (non-null assertion) que puede ocultar errores en runtime",
        "regex": r'\w+!\.\w+',
        "min_index": None,
        "extensions": [".ts", ".tsx"],
    },
    {
        "name": "ts_type_assertion_any",
        "description": "Cast a 'any' o 'as any' que elimina seguridad de tipos",
        "regex": r'(?:as\s+any|<any>)',
        "min_index": None,
        "extensions": [".ts", ".tsx"],
    },
    {
        "name": "ts_optional_chain_missing",
        "description": "Acceso a propiedad de objeto posiblemente undefined sin optional chaining",
        "regex": r'(?:props|params|options|config|data|response|result)\.\w+\.\w+',
        "min_index": None,
        "extensions": [".ts", ".tsx"],
    },
    # ─── LOGIC ERROR PATTERNS (ALL LANGUAGES) ──────────────────────
    {
        "name": "duplicate_parameter_same_var",
        "description": "Posible error: misma variable pasada dos veces como argumento (ej: func(x, x))",
        "regex": r'\(\s*(\w+)\s*,\s*\1\s*[,)]',
        "min_index": None,
        "extensions": [".cs", ".js", ".ts", ".tsx"],
    },
    {
        "name": "coord_param_order_suspect",
        "description": "Posible error de orden en coordenadas (lat/long, x/y)",
        "regex": r'(?:longitude|lng|lon)\s*,\s*(?:longitude|lng|lon)|(?:latitude|lat)\s*,\s*(?:latitude|lat)|(?:\by\b)\s*,\s*(?:\bx\b)',
        "min_index": None,
        "extensions": [".cs", ".js", ".ts", ".tsx"],
        "case_insensitive": True,
    },
    {
        "name": "copy_paste_duplicate_condition",
        "description": "Posible error copy-paste: misma condicion repetida en if/else if",
        "regex": r'if\s*\(([^)]+)\)[^}]+else\s+if\s*\(\1\)',
        "min_index": None,
        "extensions": [".cs", ".js", ".ts", ".tsx"],
    },
]

# Patrones que indican que YA existe una verificación de bounds
GUARD_PATTERNS = [
    r'\.Count\s*[>]=?\s*\d+',
    r'\.Length\s*[>]=?\s*\d+',
    r'\.Count\(\)\s*[>]=?\s*\d+',
    r'\.Any\(\)',
    r'!=\s*null\s*&&',
    r'!=\s*null\s*\?',
    r'\?\.',
    r'if\s*\(\s*\w+\s*!=\s*null',
    r'\.Count\s*==\s*\d+',
    r'\.Length\s*==\s*\d+',
    r'\.Count\(\)\s*==\s*\d+',
    r'TryParse',
    r'try\s*\{',
    r'as\s+\w+\s*;',
    r'\bis\s+\w+',
    r'string\.IsNullOrEmpty',
    r'string\.IsNullOrWhiteSpace',
    r'@if\s*\(\s*Model\s*!=\s*null',
]


def _has_guard(context_lines: List[str], current_line: str) -> bool:
    """Verifica si en las líneas de contexto previas hay una validación de bounds."""
    all_text = " ".join(context_lines) + " " + current_line
    for guard in GUARD_PATTERNS:
        if re.search(guard, all_text):
            return True
    return False


def _get_context(lines: List[str], line_idx: int, window: int = 5) -> Tuple[List[str], List[str]]:
    """Obtiene líneas de contexto antes y después del hallazgo."""
    start = max(0, line_idx - window)
    end = min(len(lines), line_idx + window + 1)
    before = [f"{start + i + 1}: {lines[start + i]}" for i in range(line_idx - start)]
    after = [f"{line_idx + 2 + i}: {lines[line_idx + 1 + i]}" for i in range(end - line_idx - 1)]
    return before, after


def scan_file(file_path: str) -> List[Finding]:
    """Escanea un archivo individual buscando patrones peligrosos."""
    findings = []
    ext = os.path.splitext(file_path)[1].lower()

    try:
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            lines = f.readlines()
    except (OSError, IOError):
        return findings

    for pattern_def in PATTERNS:
        if ext not in pattern_def["extensions"]:
            continue

        flags = re.IGNORECASE if pattern_def.get("case_insensitive") else 0
        regex = re.compile(pattern_def["regex"], flags)

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Ignorar comentarios
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            match = regex.search(line)
            if not match:
                continue

            # Para patrones con índice mínimo, verificar el valor
            if pattern_def["min_index"] is not None and match.lastindex:
                idx_value = int(match.group(1))
                if idx_value < pattern_def["min_index"]:
                    continue

            # Verificar si ya hay un guard en las líneas anteriores
            context_start = max(0, i - 5)
            context_lines = [lines[j].strip() for j in range(context_start, i)]

            if _has_guard(context_lines, stripped):
                continue

            before, after = _get_context(lines, i)

            finding = Finding(
                file_path=file_path,
                line_number=i + 1,
                line_content=stripped,
                pattern_name=pattern_def["name"],
                context_before=before,
                context_after=after,
            )
            findings.append(finding)

    return findings


def scan_directory(root_path: str, extensions: List[str] = None) -> List[Finding]:
    """Escanea recursivamente un directorio buscando patrones peligrosos."""
    if extensions is None:
        extensions = [".cs", ".js", ".ts", ".tsx", ".html", ".cshtml"]

    all_findings = []
    scanned = 0

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Ignorar directorios comunes no relevantes
        dirnames[:] = [
            d for d in dirnames
            if d not in {"bin", "obj", "node_modules", ".git", ".vs", "packages", "debug", "release"}
        ]

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in extensions:
                continue

            file_path = os.path.join(dirpath, filename)
            findings = scan_file(file_path)
            all_findings.extend(findings)
            scanned += 1

    print(f"[Scanner] Archivos escaneados: {scanned}, hallazgos: {len(all_findings)}")
    return all_findings
