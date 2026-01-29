"""
reporter.py - Genera reporte markdown con los hallazgos analizados.
"""

import os
from datetime import datetime
from typing import List
from collections import Counter
from scanner import Finding


def _severity_order(severity: str) -> int:
    """Ordena por severidad (mayor primero)."""
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "NEEDS_REVIEW": 4, "ERROR": 5, "FALSE_POSITIVE": 6}
    return order.get(severity, 99)


def _get_lang(file_path: str) -> str:
    """Detecta lenguaje para syntax highlight del markdown."""
    ext = os.path.splitext(file_path)[1].lower()
    return {".cs": "csharp", ".js": "javascript", ".html": "html", ".cshtml": "html"}.get(ext, "")


def generate_report(findings: List[Finding], output_path: str, scanned_path: str,
                    model_used: str) -> str:
    """Genera el reporte markdown completo."""

    # Filtrar false positives para el reporte principal
    real_bugs = [f for f in findings if f.severity not in ("FALSE_POSITIVE", "ERROR")]
    false_positives = [f for f in findings if f.severity == "FALSE_POSITIVE"]
    errors = [f for f in findings if f.severity == "ERROR"]

    # Ordenar por severidad
    real_bugs.sort(key=lambda f: (_severity_order(f.severity), f.file_path, f.line_number))

    # Contadores
    severity_counts = Counter(f.severity for f in real_bugs)
    file_counts = Counter(f.file_path for f in real_bugs)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append("# Reporte de Auditoria: Errores de Indices y Null Reference\n")
    lines.append(f"**Fecha:** {now}  ")
    lines.append(f"**Directorio analizado:** `{scanned_path}`  ")
    lines.append(f"**Modelo LLM utilizado:** `{model_used}`  ")
    lines.append(f"**Total de hallazgos analizados:** {len(findings)}  ")
    lines.append(f"**Bugs confirmados:** {len(real_bugs)}  ")
    lines.append(f"**Falsos positivos descartados:** {len(false_positives)}  ")
    lines.append(f"**Errores de analisis:** {len(errors)}\n")

    # Resumen ejecutivo
    lines.append("## Resumen Ejecutivo\n")
    lines.append("| Severidad | Cantidad |")
    lines.append("|-----------|----------|")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NEEDS_REVIEW"]:
        count = severity_counts.get(sev, 0)
        if count > 0:
            lines.append(f"| {sev} | {count} |")
    lines.append("")

    # Errores detallados
    if real_bugs:
        lines.append("---\n")
        lines.append("## Errores Encontrados\n")

        for i, finding in enumerate(real_bugs, 1):
            lang = _get_lang(finding.file_path)
            rel_path = finding.file_path

            lines.append(f"### [{finding.severity}] Error #{i} - {finding.pattern_name}\n")
            lines.append(f"- **Archivo:** `{rel_path}`")
            lines.append(f"- **Linea:** {finding.line_number}")
            lines.append(f"- **Patron detectado:** {finding.pattern_name}\n")

            lines.append("**Codigo con error:**")
            lines.append(f"```{lang}")
            # Contexto antes
            for ctx in finding.context_before:
                lines.append(ctx)
            lines.append(f">>> {finding.line_number}: {finding.line_content}  // <-- ERROR")
            for ctx in finding.context_after:
                lines.append(ctx)
            lines.append("```\n")

            lines.append(f"**Problema:** {finding.analysis}\n")

            if finding.suggested_fix:
                lines.append("**Solucion propuesta:**")
                lines.append(f"```{lang}")
                lines.append(finding.suggested_fix)
                lines.append("```\n")

            lines.append("---\n")

    # Tabla resumen por archivo
    if file_counts:
        lines.append("## Resumen por Archivo\n")
        lines.append("| Archivo | Errores | Severidad maxima |")
        lines.append("|---------|---------|-----------------|")

        file_max_severity = {}
        for f in real_bugs:
            current = file_max_severity.get(f.file_path, "LOW")
            if _severity_order(f.severity) < _severity_order(current):
                file_max_severity[f.file_path] = f.severity

        for file_path, count in file_counts.most_common():
            short = os.path.basename(file_path)
            max_sev = file_max_severity.get(file_path, "")
            lines.append(f"| `{short}` | {count} | {max_sev} |")
        lines.append("")

    # Falsos positivos
    if false_positives:
        lines.append("## Falsos Positivos (descartados por el LLM)\n")
        lines.append("Estos hallazgos fueron detectados por el scanner pero el LLM determino que no son bugs:\n")
        for fp in false_positives:
            lines.append(f"- `{os.path.basename(fp.file_path)}:{fp.line_number}` - {fp.analysis}")
        lines.append("")

    # Recomendaciones
    lines.append("## Recomendaciones Generales\n")
    lines.append("1. **Siempre validar bounds antes de acceder por indice:** Usar `.Count > N` o `.Length > N` antes de `collection[N]`")
    lines.append("2. **Verificar null despues de FirstOrDefault():** El resultado puede ser null si la coleccion esta vacia o no hay match")
    lines.append("3. **Verificar resultado de Split():** `string.Split()` puede retornar menos elementos de los esperados")
    lines.append("4. **Usar operador null-conditional:** Preferir `collection?.FirstOrDefault()?.Property` cuando sea apropiado")
    lines.append("5. **Validar colecciones de SharePoint:** Las listas de SharePoint pueden estar vacias o tener campos null")
    lines.append("6. **Validar configuraciones:** Los valores de `ConfigurationManager.AppSettings` pueden no tener el formato esperado")
    lines.append("")

    content = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n[Reporter] Reporte generado en: {output_path}")
    print(f"[Reporter] {len(real_bugs)} bugs documentados, {len(false_positives)} falsos positivos descartados")

    return output_path
