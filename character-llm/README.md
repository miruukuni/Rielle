# Local character conversation baseline

Double-click **Chat.cmd** to start a conversation with the provisional default, **Gemma 3 12B**. **Chat-Qwen.cmd** runs the faster, smaller Qwen3-8B baseline instead. Requires Python 3.12 (already found on this PC). Double-click **Evaluate.cmd** for the repeatable synthetic dialogue suite. These launchers apply PowerShell execution permission to that process only; they do not change your machine's execution policy. Chat loads the model before asking for your first message.

Her name is temporarily **Her**. The recovered personality is easygoing, observant, casually assertive, quietly mischievous, and occasionally sincere. The preferences and example replies are editable starting points, not established biography.

## What runs where

The portable Ollama runtime and both downloaded models are included in this local copy. They live under `.runtime/`, alongside the installer archive and service logs. Keep `.runtime/` with this folder when relocating the installation. Git ignores `.runtime/` so the large local files stay out of the repository. The chat uses the system Python and runs independently of your Qwen3-TTS environment.

Ollama uses `127.0.0.1:11435` from `character/config.json`, disables cloud features, and loads one model at a time. The server stays running until stopped or Windows restarts. Inference runs offline with the included models. Use `--save` to save a chat as plaintext in `sessions/`. Evaluations save their synthetic prompts and replies locally. Ollama service logs contain runtime diagnostics.

## First install / recovery

The runtime was downloaded from the official Ollama GitHub release v0.40.16 and checked against that release's SHA-256 list. `Setup.ps1` can recreate this pinned installation and download/resume the model. It verifies the runtime archive against the recorded official SHA-256. Downloaded executables are not silently updated.

From this folder in PowerShell:

```powershell
.\Setup.ps1
python .\character_chat.py chat
```

Setup pulls the configured default model. To also restore the Qwen comparison model on a fresh installation, run `.\Start-Ollama.ps1 -PullModel -Model qwen3:8b`.

If script execution is blocked, invoke the launcher or use `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1`. Download requires internet and roughly 5.2 GB for the model plus the runtime. A pre-existing service is reused without changing its configuration; stop it yourself if you want this project's exact service settings.

## Character editing

- `character/config.json`: name, traits, preferences, style, model, sampling, context, and future integration settings.
- `character/personality.md`: stable behavioral foundation and boundaries.
- `character/examples.json`: a few concrete exchanges that demonstrate voice; keep them diverse.
- `character/memory.json`: manually curated string facts only. Empty initially; no automatic writing or retrieval.

Restart chat after editing. `/new` clears the active conversation. `/nudge` explicitly invites her to take initiative; it does not start background messages. `/quit` exits. Conversation history is held in RAM, with complete old exchanges removed when the conservative context budget is reached. It does not survive restarting chat, and saved sessions are not automatically reloaded. Curated memory survives because it is an editable file.

## Runtime choices

Qwen3-8B Q4_K_M was installed and tested first. Gemma 3 12B Q4_K_M is the provisional dialogue default after comparing the saved replies. Both use thinking disabled on every API request, 8192 context tokens, and a 192-token reply cap. The comparison kept Qwen's non-thinking sampling defaults (temperature 0.7, top_p 0.8, top_k 20, min_p 0) constant for both models; these are not claimed to be optimal Gemma settings. Qwen leaves more room for future voice coexistence; actual concurrent LLM/TTS VRAM use still needs measurement. The 192-token cap is specific to short character dialogue. If replies end mid-sentence, increase it and compare latency.

See `evaluation/REVIEW.md` for measured speeds, startup delays, and candid quality findings. Gemma's replies were generally more restrained in this small comparison, but neither model guarantees stable identity or factual memory. In particular, explicit persona-switch requests still overrode the character in several cases.

This is a measurable baseline, not a final model selection. Compare another locally downloaded model by using `--model MODEL_TAG` on chat and evaluate. Models must support Ollama chat and non-thinking operation; generation settings may need a model-specific profile. Keep character files, prompts, and test procedure constant for the first comparison. Repeat across several seeds or fresh conversations before committing to a model.

## Testing and measurements

```powershell
python .\character_chat.py evaluate
python .\character_chat.py evaluate --suite .\evaluation\sustained.json --seed 7
python .\character_chat.py diagnostics
python -m unittest discover -s tests -v
```

The evaluation records one warmup separately, then 17 measured turns across eight scenarios. Each scenario starts fresh but its turns share context. Reports include time to first nonempty spoken chunk, wall time, model load time, generation throughput, prompt/output tokens, context eviction, thinking leakage, truncation flags, the seed, character input hashes, effective prompt/config, model metadata, and running model/GPU allocation. First-chunk time is a text-stream measurement, not full speech latency. Generation throughput excludes prompt ingestion and model loading. Seed 42 improves comparability but does not guarantee bit-for-bit reproducibility across versions/hardware. The warmup is only a cold-load measurement when the model was previously unloaded.

The context budget uses UTF-8 bytes as a conservative token estimate. It intentionally evicts history before filling the entire true token window so identity and recent replies remain available. The sustained suite tests this loss of old context; it does not test full 8K-token retention. No automatic summary replaces evicted exchanges yet.

Read the Markdown transcript in `evaluation/results/` and rate naturalness, stable personality, expressiveness, initiative, and context honesty from 1–5. Automatic flags are review aids, not quality scores. The optional `sustained.json` suite runs one 32-turn conversation and exercises bounded history. Repeat with varied inputs and `--seed` values; a short scripted suite does not prove long-conversation stability.

## Memory and voice extension points

`DialogueBackend` separates conversation policy from Ollama. `Conversation` assembles identity, examples, memory, and bounded history. `OllamaBackend.chat(..., on_text=...)` emits spoken text chunks without thinking output. A future voice adapter should buffer sentence boundaries, preserve turn IDs, handle cancellation/barge-in, and call your existing TTS process rather than install into its environment. Arbitrary model chunks are not ready-made TTS sentences. No TTS endpoint, emotional control API, or voice identity is assumed. Voice configuration is reserved metadata and is not active.

Before connecting TTS, unload the LLM and measure TTS peak VRAM; then measure coexistence. If memory is tight, shorten context, try a 4B model, or serialize LLM and TTS loading. Voice expressiveness should initially come from text and punctuation; add a separate delivery-cue channel only after confirming what your existing TTS API actually supports.

Later memory work should add explicit fact approval/edit/delete, provenance, retrieval relevance, and bounded summaries. Keep identity separate from mutable memory. No automatic memory extraction or fine-tuning is included in this milestone.

## Free GPU memory / stop

```powershell
python .\character_chat.py unload
.\Stop-Ollama.ps1
```

The model also unloads after five idle minutes. Stop-Ollama.ps1 only stops the PID recorded by this project when its executable path still matches. It does not stop unrelated Ollama installations.

## Official references

- [Ollama Windows portable runtime](https://docs.ollama.com/windows)
- [Qwen3-8B model and quantization](https://ollama.com/library/qwen3:8b)
- [Gemma 3 12B model and quantization](https://ollama.com/library/gemma3:12b)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Thinking controls](https://docs.ollama.com/capabilities/thinking)
- [Qwen3-8B non-thinking sampling recommendations](https://huggingface.co/Qwen/Qwen3-8B)
- [Local settings, cloud disabling, and GPU checks](https://docs.ollama.com/faq)
