"""
analyzer.py - Envía hallazgos al LLM elegido para análisis y sugerencia de fix.
Usa litellm para soporte multi-provider (Ollama, OpenAI, Anthropic, etc).
"""

import json
from typing import List
from scanner import Finding

litellm = None


def _ensure_litellm():
    """Importa litellm bajo demanda para que --no-llm funcione sin la dependencia."""
    global litellm
    if litellm is None:
        try:
            import litellm as _litellm
            _litellm.suppress_debug_info = True
            litellm = _litellm
        except ImportError:
            print("Error: litellm no esta instalado. Ejecuta: pip install litellm")
            print("       O usa --no-llm para ejecutar solo el scanner.")
            raise SystemExit(1)

SYSTEM_PROMPT = """You are a senior code auditor. Your task is to determine if a code fragment can CRASH at runtime OR contains LOGIC ERRORS that produce incorrect behavior.

You must analyze code in: C#, JavaScript, TypeScript, HTML, and Razor views.

== RUNTIME CRASH SCENARIOS ==

1. INDEX OUT OF BOUNDS: Accessing array[N] or list[N] when the collection may have fewer than N+1 elements.
   Example: items[5].Value when items only has 3 elements. Split('"')[1] when the string has no quotes.

2. NULL REFERENCE: Using .Property or .Method() on something that can be null.
   Example: object.Name when object could be null. FirstOrDefault().Id without null check.

3. INVALID CAST: Casting without checking type first.
   Example: (FieldLookupValue)oListItem["Field"] when the field could be a different type or null.

4. FORMAT / PARSE EXCEPTION: Using int.Parse(), DateTime.Parse(), decimal.Parse() on user input or external data without TryParse.
   Example: int.Parse(Request["id"]) when id could be "abc".

5. DIVISION BY ZERO: Dividing by a variable that could be zero.
   Example: total / count when count comes from a query that could return 0.

6. EMPTY COLLECTION ACCESS: Calling .First(), [0], .Single() on a collection that could be empty.
   Example: list[0].Name when list comes from a database query that could return 0 rows.

7. NULL STRING OPERATIONS: Calling .ToString(), .Split(), .Trim(), .ToLower() on a value that could be null.
   Example: oListItem["Field"].ToString() when the field value is null.

8. DISPOSED / CLOSED RESOURCE: Using an object after it could be disposed or a connection after it could be closed.

9. JAVASCRIPT / TYPESCRIPT / RAZOR CRASHES:
   - document.getElementById("x").value when element might not exist
   - @Model.Property in Razor when Model could be null
   - querySelectorAll()[N] without checking length
   - JSON.parse() on invalid string
   - TypeScript: accessing properties on possibly undefined values despite type assertions

10. UNVALIDATED EXTERNAL DATA: Data from database, API, SharePoint, config files, or user input used directly without validation.
    Example: ConfigurationManager.AppSettings["key"].ToString() when the key might not exist.

== LOGIC / SEMANTIC ERRORS ==

11. PARAMETER ORDER SWAP: Arguments passed in wrong order due to similar types. This is a CRITICAL logic bug.
    Example: setCoordinates(longitude, longitude) instead of setCoordinates(longitude, latitude)
    Example: copyFile(destination, source) instead of copyFile(source, destination)
    Example: calculate(width, width) instead of calculate(width, height)
    Example: compare(expected, actual) when API expects compare(actual, expected)
    Example: new Point(y, x) instead of new Point(x, y)
    LOOK FOR: Functions with 2+ parameters of the same type where the same variable is passed twice, or variables seem swapped based on naming conventions.

12. WRONG VARIABLE USED: Using a similar-named variable instead of the correct one.
    Example: Using 'userId' instead of 'customerId' in a customer query
    Example: Using 'startDate' for both start and end parameters
    Example: Using 'request' object when 'response' was intended
    Example: Using loop variable from outer loop in inner loop

13. COPY-PASTE ERRORS: Code that appears duplicated with incomplete modifications.
    Example: if (x > 0) { doX(); } else if (x > 0) { doY(); } // second condition should be different
    Example: setWidth(value); setWidth(value); // second should be setHeight

14. BOOLEAN LOGIC ERRORS: Conditions that are always true/false or inverted.
    Example: if (x > 5 && x < 3) // impossible condition
    Example: if (isValid == false) when if (!isValid) was intended but logic is inverted
    Example: while (list.length > 0) { } // infinite loop if nothing removes from list

15. OFF-BY-ONE ERRORS: Incorrect loop bounds or index calculations.
    Example: for (i = 0; i <= array.length; i++) // should be < not <=
    Example: substring(0, length - 1) when full string was intended

RESPONSE FORMAT - Reply ONLY with valid JSON, no markdown, no explanation outside the JSON:
{
  "is_bug": true,
  "severity": "CRITICAL",
  "crash_type": "INDEX_OUT_OF_BOUNDS",
  "what_breaks": "items[5].Value crashes because items may have fewer than 6 elements",
  "when_breaks": "When the SharePoint list returns fewer items than expected",
  "original_code": "var x = items[5].Value;",
  "fixed_code": "var x = items.Count > 5 ? items[5].Value : string.Empty;",
  "explanation": "Brief explanation of the root cause"
}

CRASH_TYPE VALUES (use these exact strings):
- Runtime crashes: INDEX_OUT_OF_BOUNDS, NULL_REFERENCE, INVALID_CAST, PARSE_EXCEPTION, DIVISION_BY_ZERO, EMPTY_COLLECTION, NULL_STRING_OP, DISPOSED_RESOURCE, UNVALIDATED_DATA
- Logic errors: PARAMETER_ORDER_SWAP, WRONG_VARIABLE, COPY_PASTE_ERROR, BOOLEAN_LOGIC_ERROR, OFF_BY_ONE

SEVERITY RULES:
- CRITICAL: Will crash with normal production data OR logic error that produces clearly wrong results (swapped lat/long, wrong ID used)
- HIGH: Will crash with real edge-case data OR logic error that affects calculations/data integrity
- MEDIUM: Could crash with unusual but possible data OR logic error with limited impact
- LOW: Unlikely to crash but technically unsafe, or minor logic inconsistency
- FALSE_POSITIVE: Not a real bug, there IS protection the scanner missed (check carefully!)

IMPORTANT:
- The "fixed_code" field must contain ONLY valid code ready to copy-paste, NO explanatory text
- The "original_code" field must contain the exact line(s) that need to change
- If the code is actually safe (has a guard/check), set is_bug to false
- Respond with ONLY the JSON object, nothing else"""


def _build_user_prompt(finding: Finding) -> str:
    """Construye el prompt con el contexto del hallazgo."""
    context_before = "\n".join(finding.context_before) if finding.context_before else "(no prior context)"
    context_after = "\n".join(finding.context_after) if finding.context_after else "(no following context)"

    return f"""Analyze this code for runtime crash risk:

File: {finding.file_path}
Line: {finding.line_number}
Detected pattern: {finding.pattern_name}

Context before:
{context_before}

>>> SUSPECT LINE (line {finding.line_number}):
{finding.line_content}

Context after:
{context_after}

Can this code crash at runtime? If yes, what exact scenario causes the crash and what is the fix?"""


def analyze_finding(finding: Finding, model: str, api_base: str = None) -> Finding:
    """Analiza un hallazgo individual usando el LLM."""
    _ensure_litellm()
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(finding)},
        ],
        "temperature": 0.1,
        "max_tokens": 1000,
    }

    if api_base:
        kwargs["api_base"] = api_base

    try:
        response = litellm.completion(**kwargs)
        content = response.choices[0].message.content.strip()

        # Limpiar posible markdown wrapping
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        result = json.loads(content)

        finding.severity = result.get("severity", "UNKNOWN")

        # Construir análisis completo desde los campos nuevos
        crash_type = result.get("crash_type", "")
        what_breaks = result.get("what_breaks", "")
        when_breaks = result.get("when_breaks", "")
        explanation = result.get("explanation", "")

        parts = []
        if crash_type:
            parts.append(f"[{crash_type}]")
        if what_breaks:
            parts.append(what_breaks)
        elif explanation:
            parts.append(explanation)
        if when_breaks:
            parts.append(f"Se rompe cuando: {when_breaks}")
        finding.analysis = " ".join(parts) if parts else explanation

        # Código original y fix separados
        original = result.get("original_code", "")
        fixed = result.get("fixed_code", "")
        if original and fixed:
            finding.suggested_fix = f"// ANTES:\n{original}\n\n// DESPUES:\n{fixed}"
        elif fixed:
            finding.suggested_fix = fixed
        else:
            finding.suggested_fix = result.get("suggested_fix", "")

        if not result.get("is_bug", True):
            finding.severity = "FALSE_POSITIVE"

    except json.JSONDecodeError:
        # Si el LLM no devolvió JSON válido, usar la respuesta raw
        finding.severity = "NEEDS_REVIEW"
        finding.analysis = content if 'content' in dir() else "Error parsing LLM response"
        finding.suggested_fix = ""
    except Exception as e:
        finding.severity = "ERROR"
        finding.analysis = f"Error al comunicarse con el LLM: {str(e)}"
        finding.suggested_fix = ""

    return finding


def analyze_findings(findings: List[Finding], model: str, api_base: str = None,
                     batch_size: int = 5) -> List[Finding]:
    """Analiza todos los hallazgos, mostrando progreso."""
    total = len(findings)
    analyzed = []

    for i, finding in enumerate(findings):
        print(f"[Analyzer] Analizando {i + 1}/{total}: {finding.file_path}:{finding.line_number} ({finding.pattern_name})")
        result = analyze_finding(finding, model, api_base)
        analyzed.append(result)

        # Mostrar resultado inmediato
        icon = {
            "CRITICAL": "!!",
            "HIGH": "! ",
            "MEDIUM": "~ ",
            "LOW": "  ",
            "FALSE_POSITIVE": "OK",
            "ERROR": "XX",
            "NEEDS_REVIEW": "??",
        }.get(result.severity, "??")
        print(f"         [{icon}] {result.severity}: {result.analysis[:80]}")

    # Resumen
    severities = {}
    for f in analyzed:
        severities[f.severity] = severities.get(f.severity, 0) + 1

    print(f"\n[Analyzer] Resumen: {severities}")
    return analyzed
