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
git clone https://github.com/centralcordoba/agentAIQA.git
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

## 🦙 Guía Completa: Instalar Ollama + DeepSeek (GRATIS)

Ollama te permite ejecutar modelos de IA **localmente en tu PC**, sin costo y con total privacidad. Tu código nunca sale de tu máquina.

### 1️⃣ Descargar Ollama

#### Windows

1. Ve a **https://ollama.com/download**
2. Click en **"Download for Windows"**
3. Ejecuta el instalador `OllamaSetup.exe`
4. Sigue el wizard (Next → Next → Install → Finish)

#### macOS

```bash
# Opción 1: Descarga directa
# Ve a https://ollama.com/download y descarga el .dmg

# Opción 2: Con Homebrew
brew install ollama
```

#### Linux

```bash
# Instalación con una línea
curl -fsSL https://ollama.com/install.sh | sh
```

---

### 2️⃣ Verificar la Instalación

Abre una **nueva terminal** (CMD, PowerShell, o Terminal) y ejecuta:

```bash
ollama --version
```

Deberías ver algo como:
```
ollama version 0.5.4
```

Si dice "command not found", reinicia tu terminal o PC.

---

### 3️⃣ Iniciar el Servicio Ollama

#### Windows
Ollama se inicia automáticamente. Busca el ícono 🦙 en la bandeja del sistema (esquina inferior derecha).

#### macOS / Linux
```bash
# Iniciar el servicio
ollama serve
```

> 💡 **Tip:** En Windows, Ollama corre como servicio en background. En Linux/Mac puedes dejarlo corriendo en una terminal separada.

#### Verificar que está corriendo

```bash
# Debe responder con la lista de modelos (vacía al inicio)
ollama list
```

Salida esperada:
```
NAME    ID    SIZE    MODIFIED
```

---

### 4️⃣ Descargar DeepSeek (Modelo Gratuito)

DeepSeek es un modelo de código abierto excelente para análisis de código. Hay varias versiones:

#### Opción A: DeepSeek Coder V2 (Recomendado para análisis de código)

```bash
# 16GB de RAM recomendados
ollama pull deepseek-coder-v2:16b
```

#### Opción B: DeepSeek R1 (Mejor razonamiento)

```bash
# Excelente para detectar bugs complejos
ollama pull deepseek-r1:14b
```

#### Opción C: DeepSeek R1 Distill (Más ligero)

```bash
# Para PCs con menos recursos (8GB RAM)
ollama pull deepseek-r1:7b
```

#### Opción D: DeepCoder (Optimizado para código)

```bash
# Muy bueno para auditoría de código
ollama pull deepcoder:14b
```

> ⏳ **La descarga puede tardar** dependiendo de tu conexión:
> - Modelos 7B: ~4GB, 5-10 minutos
> - Modelos 14B: ~8GB, 10-20 minutos
> - Modelos 16B: ~9GB, 15-25 minutos

---

### 5️⃣ Verificar el Modelo Descargado

```bash
ollama list
```

Salida esperada:
```
NAME                    ID              SIZE      MODIFIED
deepseek-r1:14b         abc123def456    8.9 GB    2 minutes ago
```

---

### 6️⃣ Probar el Modelo (Opcional)

Puedes chatear directamente con el modelo para verificar que funciona:

```bash
ollama run deepseek-r1:14b
```

Escribe una pregunta de prueba:
```
>>> ¿Qué bug tiene este código? var x = list[0];
```

Para salir del chat: `Ctrl+D` o escribe `/bye`

---

### 7️⃣ Ejecutar el Agente con Ollama

Ahora puedes usar el agente con tu modelo local:

```bash
# Usando el menú interactivo
python main.py

# O directamente por CLI
python main.py --path ./tu-proyecto --provider ollama --model ollama/deepseek-r1:14b
```

---

### 🔧 Troubleshooting

#### "Error: model not found"
```bash
# Verifica que el modelo está descargado
ollama list

# Si no aparece, descárgalo de nuevo
ollama pull deepseek-r1:14b
```

#### "Error: connection refused"
```bash
# Ollama no está corriendo. Inícialo:
ollama serve

# O en Windows, busca el ícono en la bandeja y click derecho → Start
```

#### "Error: out of memory"
```bash
# Tu modelo es muy grande para tu RAM. Usa uno más pequeño:
ollama pull deepseek-r1:7b
```

#### Verificar que Ollama responde
```bash
# Debe retornar una respuesta JSON
curl http://localhost:11434/api/tags
```

---

### 📊 Comparativa de Modelos para Análisis de Código

| Modelo | Tamaño | RAM Mínima | Velocidad | Calidad | Uso Recomendado |
|--------|--------|------------|-----------|---------|-----------------|
| `deepcoder:1.5b` | 1GB | 4GB | ⚡⚡⚡⚡⚡ | ⭐⭐ | Testing rápido |
| `deepseek-r1:7b` | 4GB | 8GB | ⚡⚡⚡⚡ | ⭐⭐⭐ | PCs modestas |
| `deepcoder:14b` | 8GB | 16GB | ⚡⚡⚡ | ⭐⭐⭐⭐ | Balance ideal |
| `deepseek-r1:14b` | 9GB | 16GB | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | Mejor razonamiento |
| `deepseek-coder-v2:16b` | 9GB | 16GB | ⚡⚡ | ⭐⭐⭐⭐⭐ | Código complejo |

---

### 💡 Tips para Mejor Rendimiento

1. **Cierra otras aplicaciones** que consuman RAM antes de correr el modelo
2. **GPU NVIDIA**: Ollama usa CUDA automáticamente si tienes una GPU compatible
3. **SSD recomendado**: Los modelos cargan más rápido desde SSD que HDD
4. **Primera ejecución lenta**: El modelo se carga en memoria la primera vez, luego es más rápido

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
