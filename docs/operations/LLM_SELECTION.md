# LLM Selection Record: Tier 2 Fact Extraction
# Date: 2026-05-11
# Target: Mac Mini (24GB RAM) Control Plane

## 1. Selected Model
- **Model Name:** `gemma4:latest` (Gemma 2 9B variant)
- **Selection Date:** 2026-05-11
- **Primary Use:** Tier 2 Signal Filtering & Fact Extraction

## 2. Comparison Context
Compared `gemma4:latest` (8B) against `gemma2:27b` using a technical article benchmark (Fact Extraction Task).

| Metric | Gemma 4 (8B) | Gemma 2 (27B) |
| --- | --- | --- |
| **Latency (First Run)** | ~81s | ~105s |
| **Resource Impact** | Low (9.6GB) | High (15GB+) - Swapping Risk |
| **Extraction Density** | High (Granular figures captured) | Moderate (Summarized output) |
| **Stability on Mac Mini** | High (Co-exists with other tasks) | Low (System slowdown detected) |

## 3. Rationale for Selection

1. **Memory Efficiency:** The Mac Mini has 24GB of unified memory. Running a 27B model (15GB) along with the OS, Postgres, and Ollama background tasks pushes the memory to the limit (~23GB used), causing UI and SSH sluggishness. The 9B model allows for a healthy buffer.
2. **Extraction Granularity:** For the specific task of extracting costs, market sizes, and performance metrics, the smaller model proved to be more "literal" and captured more specific numbers from the text, whereas the larger model tended to generalize.
3. **Pipeline Throughput:** Tier 1 scrapes hundreds of articles. A 25-30% speed advantage per article significantly reduces the total pipeline turnaround time.

## 4. Implementation Details
- `.env` set to `OLLAMA_MODEL=gemma4:latest`
- `OLLAMA_HOST=http://localhost:11434`
- Prompt optimized for JSON output.

---
*Note: This record serves as a baseline to avoid repeated benchmarking of the 27B model unless a significant reasoning-heavy task (Tier 3+) is delegated to the local host.*
