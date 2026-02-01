# 🐛 Code Audit Agent

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/LLM-Powered-purple?style=for-the-badge&logo=openai&logoColor=white" alt="LLM">
  <img src="https://img.shields.io/badge/C%23-Runtime_Errors-239120?style=for-the-badge&logo=csharp&logoColor=white" alt="C#">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

<p align="center">
  <strong>🔍 Detecta errores de runtime antes de que lleguen a producción</strong>
</p>

<p align="center">
  <em>Análisis estático de código C#, JavaScript, TypeScript y Razor para encontrar crashes potenciales</em>
</p>

<p align="center">
  <a href="https://agents.boyscout.dev">
    <img src="https://img.shields.io/badge/🤖_agents.boyscout.dev-AI_Agents_Collection-orange?style=for-the-badge" alt="agents.boyscout.dev">
  </a>
</p>

---

## ⚡ Quick Start

```bash
# Clonar e instalar
git clone https://github.com/your-repo/agentAIQA.git
cd agentAIQA
pip install -r requirements.txt

# Ejecutar (modo interactivo)
python main.py

# O modo CLI rápido
python main.py --path /tu/proyecto --no-llm
```

---

## 🎯 ¿Qué detecta?

<table>
<tr>
<td width="50%">

### 💥 Runtime Crashes

- **Index Out of Bounds**
  - `array[5]` sin verificar `.Count`
  - `Split()[1]` sin validar resultado
  - `ToList()[0]` en colección vacía

- **Null Reference**
  - `FirstOrDefault().Property`
  - `object.Method()` sin null check
  - `oListItem["Field"].ToString()`

- **Parse Exceptions**
  - `int.Parse()` sin `TryParse`
  - `DateTime.Parse()` en datos externos
  - `Convert.ToInt32()` sin validación

</td>
<td width="50%">

### 🧠 Logic Errors

- **Parameter Order Swap**
  - `func(x, x)` mismo parámetro dos veces
  - `setCoords(lng, lng)` en vez de `(lat, lng)`
  - Argumentos intercambiados por tipo similar

- **Copy-Paste Errors**
  - `if (x > 0) {} else if (x > 0) {}`
  - Condiciones duplicadas
  - Variables equivocadas

- **Off-by-One**
  - `for (i <= length)` en vez de `<`
  - Índices incorrectos en loops

</td>
</tr>
<tr>
<td width="50%">

### 🔄 Unsafe Operations

- **Invalid Cast**
  - `(FieldLookupValue)item["Field"]`
  - Cast directo sin `as` o `is`

- **Division by Zero**
  - `total / count` sin verificar

- **Disposed Resources**
  - Uso después de `Dispose()`
  - Conexiones cerradas

</td>
<td width="50%">

### 🌐 JavaScript / TypeScript / Razor

- `getElementById().value` sin null check
- `querySelectorAll()[0]` sin verificar length
- `JSON.parse()` sin try-catch
- `@Model.Property` sin verificar null
- Non-null assertion `!` que oculta errores
- `as any` que elimina type safety

</td>
</tr>
</table>

---

## 🛡️ Guardas Reconocidas

El scanner **NO reporta** si detecta protecciones existentes:

```csharp
// ✅ Estas protecciones son reconocidas:
if (items.Count > 0) { items[0]... }     // Count check
if (obj != null) { obj.Method() }         // Null check
items?.FirstOrDefault()?.Property         // Null conditional
int.TryParse(input, out var result)       // TryParse
var item = obj as MyType;                 // Safe cast
if (string.IsNullOrEmpty(str)) { }        // String validation
```

---

## 🚀 Modos de Uso

### 1️⃣ Menú Interactivo (Recomendado)

```bash
python main.py
```

```
============================================================
  CODE AUDIT AGENT - Configuración
============================================================

  --- PASO 1: Directorio a analizar ---

  Directorios detectados:

  [1] MiProyecto/ (repositorio completo)
  [2] src/
  [3] Controllers/
  [4] Escribir otra ruta...

  Elige directorio (default: 1):
```

### 2️⃣ CLI Directo

```bash
# Solo scanner (rápido)
python main.py --path ./src --no-llm

# Con Ollama (local, gratis)
python main.py --path ./src --provider ollama --model ollama/deepcoder:14b

# Con OpenAI
python main.py --path ./src --provider openai --model gpt-4o

# Con Anthropic
python main.py --path ./src --provider anthropic --model claude-sonnet-4-20250514
```

### 3️⃣ Opciones CLI

| Flag | Descripción |
|------|-------------|
| `-p, --path` | Directorio a analizar |
| `-m, --model` | Modelo LLM a usar |
| `--provider` | `ollama`, `openai`, `anthropic` |
| `-o, --output` | Ruta del reporte de salida |
| `-e, --extensions` | Extensiones a escanear (`.cs .js .html .cshtml`) |
| `--no-llm` | Solo scanner, sin análisis LLM |
| `-i, --interactive` | Forzar menú interactivo |

---

## 📊 Ejemplo de Reporte

```markdown
# Reporte de Auditoría: Errores de Índices y Null Reference

**Fecha:** 2024-01-29 15:30
**Bugs confirmados:** 12
**Falsos positivos descartados:** 5

## Resumen Ejecutivo

| Severidad | Cantidad |
|-----------|----------|
| CRITICAL  | 3        |
| HIGH      | 5        |
| MEDIUM    | 4        |

---

### [CRITICAL] Error #1 - split_with_index

- **Archivo:** `Utils/Parser.cs`
- **Línea:** 45

**Código con error:**
```csharp
>>> 45: var value = input.Split('"')[1];  // <-- ERROR
```

**Problema:** [INDEX_OUT_OF_BOUNDS] Split puede retornar menos elementos.
Se rompe cuando: El string no contiene comillas.

**Solución propuesta:**
```csharp
// ANTES:
var value = input.Split('"')[1];

// DESPUÉS:
var parts = input.Split('"');
var value = parts.Length > 1 ? parts[1] : string.Empty;
```
```

---

## 🏗️ Arquitectura

```
agentAIQA/
├── main.py          # 🎮 Entry point + menú interactivo
├── scanner.py       # 🔍 Motor de detección (25+ patrones)
├── analyzer.py      # 🧠 Integración con LLMs
├── reporter.py      # 📄 Generador de reportes
├── config.json      # ⚙️ Configuración persistente
└── requirements.txt # 📦 Dependencias
```

### Pipeline de Análisis

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    SCANNER      │────▶│    ANALYZER     │────▶│    REPORTER     │
│                 │     │                 │     │                 │
│  • 25+ patterns │     │  • Confirma bug │     │  • Risk summary │
│  • Detect guards│     │  • Clasifica    │     │  • Code context │
│  • Get context  │     │  • Sugiere fix  │     │  • Fixes        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 🤖 Proveedores LLM Soportados

| Provider | Modelo Recomendado | Características |
|----------|-------------------|-----------------|
| **Ollama** | `deepcoder:14b` | 🏠 Local, gratis, privado |
| | `deepseek-r1:14b` | 🧠 Gran razonamiento |
| | `qwen2.5-coder:14b` | ⚡ Muy sólido |
| **OpenAI** | `gpt-4o` | 🎯 Mejor precisión |
| | `gpt-4o-mini` | 💰 Más económico |
| **Anthropic** | `claude-sonnet-4-20250514` | 🔥 Excelente para código |

---

## 📋 Severidades

| Nivel | Descripción | Ejemplo |
|-------|-------------|---------|
| 🔴 **CRITICAL** | Crash en flujo normal de producción | `list[0]` en query que puede estar vacía |
| 🟠 **HIGH** | Crash con datos de edge-case reales | `Split()[2]` en formato variable |
| 🟡 **MEDIUM** | Crash con datos inusuales | Parse sin TryParse en config |
| 🔵 **LOW** | Improbable pero técnicamente inseguro | Cast sin verificación |
| ✅ **FALSE_POSITIVE** | No es un bug real | El scanner detectó pero hay guard |

---

## 🛠️ Patrones Detectados

### C# (.cs)
- `hardcoded_index_access` - Acceso a índice hardcodeado
- `split_with_index` - Split seguido de índice
- `first_or_default_deref` - FirstOrDefault sin null check
- `tolist_with_index` - ToList/ToArray con índice
- `parse_without_tryparse` - Parse sin TryParse
- `tostring_on_nullable` - ToString en valor nullable
- `first_single_no_check` - First/Single/Last sin verificar
- `cast_without_as_or_is` - Cast directo peligroso
- `duplicate_parameter_same_var` - Mismo parámetro dos veces

### JavaScript/TypeScript (.js, .ts, .tsx)
- `js_queryselector_index` - querySelectorAll con índice
- `js_getelementbyid_direct` - getElementById sin null check
- `js_json_parse_no_try` - JSON.parse sin try-catch
- `ts_non_null_assertion` - Uso de `!` peligroso
- `ts_type_assertion_any` - Cast a `any`

### Razor (.cshtml)
- `razor_model_direct` - @Model.Property sin null check

---

## 📚 Casos de Uso

### 1. Auditoría Pre-Deploy
```bash
# Escanear antes de cada release
python main.py --path ./src --provider openai -o pre-deploy-audit.md
```

### 2. Code Review Automatizado
```bash
# Integrar en CI/CD
python main.py --path ./changed-files --no-llm --output review.md
```

### 3. Análisis de Código Legacy
```bash
# Encontrar bugs en código heredado
python main.py --path ./legacy-module --provider ollama
```

---

## 🤝 Contribuir

¿Encontraste un patrón que falta? ¿Quieres mejorar la detección?

1. Fork el repo
2. Crea tu branch (`git checkout -b feature/nuevo-patron`)
3. Agrega tu patrón en `scanner.py`
4. Commit (`git commit -m 'Add: detector de X'`)
5. Push (`git push origin feature/nuevo-patron`)
6. Abre un Pull Request

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para más detalles.

---

<p align="center">
  <strong>Parte de la colección de agentes de IA</strong>
</p>

<p align="center">
  <a href="https://agents.boyscout.dev">
    <img src="https://img.shields.io/badge/🤖_Más_agentes_en-agents.boyscout.dev-blue?style=for-the-badge" alt="agents.boyscout.dev">
  </a>
</p>

<p align="center">
  <sub>Made with ❤️ by the boyscout.dev team</sub>
</p>
