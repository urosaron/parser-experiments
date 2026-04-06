# Holodeck Parser Experiments

Test harness for evaluating LLM-based voice command parsers for the Holodeck
3D virtual environment.

---

## Files

| File | Purpose |
|---|---|
| `test_parser.py` | Quick single-case tester — edit transcript/scene at the top, run, see raw output |
| `test_cases.py` | 20 hand-written test cases covering all command types |
| `eval.py` | Runs all test cases and scores the model on valid JSON, command accuracy, and ID resolution |
| `eval_e2e.py` | End-to-end eval: transcript → LLM parser → RAG → final resolved command |
| `rag/` | Minimal RAG implementation (synthetic asset library + ChromaDB index + resolver + eval) |
| `docs/` | Architecture + RAG writeups and results |

---

## Prerequisites

- [Ollama](https://ollama.com) installed and running (`ollama serve`)
- Python 3.10+

---

## Setup

1. **Create and activate the virtual environment**

   macOS / Linux:

   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

   Windows (PowerShell):

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**

   macOS / Linux:

   ```bash
   pip install -r requirements.txt
   ```

   Windows (PowerShell):

   ```powershell
   pip install -r requirements.txt
   ```

3. **Pull the model** (only needed once per model)

   Parser model:

   ```powershell
   ollama pull qwen3.5:9b
   ```

   Embedding model (required for RAG indexing/query):

   ```powershell
   ollama pull qwen3-embedding:8b
   ```

---

## Quick single-case test

Edit `TEST_TRANSCRIPT` and `TEST_SCENE` at the top of `test_parser.py`, then:

macOS / Linux:

```bash
python test_parser.py
```

Windows (PowerShell):

```powershell
.\venv\Scripts\python.exe test_parser.py
```

The script prints the user message sent to the model and the raw JSON response.

---

## Running the full eval

macOS / Linux:

```bash
python eval.py
```

Windows (PowerShell):

```powershell
.\venv\Scripts\python.exe eval.py
```

Sample output:

```
Model  : qwen3.5:9b
Cases  : 20

Case                           Category               JSON    Command         ID       ms
--------------------------------------------------------------------------------------------
rel_move_left_bit              relative_move          PASS       PASS       PASS      843
rel_move_forward_few           relative_move          PASS       PASS       PASS      761
...

Total cases : 20
Valid JSON  : 19/20
Command     : 18/20
ID          : 16/17  (cases with expected id)
```

### Filtering

Run only one category:

```powershell
.\venv\Scripts\python.exe eval.py --category relative_move
```

Run a single case by id:

```powershell
.\venv\Scripts\python.exe eval.py --case point_target_resolution
```

---

## Swapping the model

macOS / Linux:

```bash
python eval.py --model qwen3.5:14b
```

Windows (PowerShell):

```powershell
.\venv\Scripts\python.exe eval.py --model qwen3.5:14b
```

Or change the default at the top of `test_parser.py` for the single-case runner.

Pull any new model first:

```powershell
ollama pull <model-name>
```

Common alternatives:

| Model | Size | Notes |
|---|---|---|
| `qwen3.5:9b` | 6.6 GB | Default — good balance |
| `qwen3.5:14b` | ~9 GB | More capable |
| `llama3.1:8b` | 4.7 GB | Meta alternative |
| `mistral:7b` | 4.1 GB | Fast, lightweight |

---

## Iterating on the system prompt

`SYSTEM_PROMPT` lives at the top of `test_parser.py` and is imported by `eval.py`.
Edit it there — changes apply to both the single-case runner and the full eval.

---

## RAG (asset resolution for spawn commands)

The repo includes a minimal RAG layer under `rag/` that resolves `asset_query` (from spawn commands) to a concrete `asset_url` by semantic search.

- **Synthetic asset library**: `rag/assets.py` (name + description + URL)
- **Indexer**: `rag/index.py` (builds a persistent ChromaDB collection under `rag/chroma_db/`)
- **Resolver**: `rag/query.py` (`AssetResolver` embeds the query and returns the closest URL)
- **RAG eval**: `rag/eval_rag.py` (retrieval-only test cases)

### Build the asset index (required once)

If the index is empty, `AssetResolver` will fail until you build it.

macOS / Linux:

```bash
python -m rag.index
```

Windows (PowerShell):

```powershell
.\venv\Scripts\python.exe -m rag.index
```

### Run the retrieval-only RAG eval

macOS / Linux:

```bash
python -m rag.eval_rag
```

Windows (PowerShell):

```powershell
.\venv\Scripts\python.exe -m rag.eval_rag
```

### Run the end-to-end pipeline eval (parser → RAG)

macOS / Linux:

```bash
python eval_e2e.py
```

Windows (PowerShell):

```powershell
.\venv\Scripts\python.exe eval_e2e.py
```

---

## Test case coverage

| Category | Count |
|---|---|
| Relative move | 5 |
| Absolute move | 2 |
| Delete | 2 |
| Spawn | 2 |
| Visibility (hide/show) | 2 |
| Rotate | 1 |
| Scale | 1 |
| No command | 2 |
| Ambiguous reference | 2 |
| Unresolvable object | 1 |
| **Total** | **20** |
