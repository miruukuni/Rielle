# Local character baseline review

Measured on November 17, 2026 on this PC: RTX 5070 Ti 16 GB, driver 621.01, Python 3.12.10, Ollama 0.40.16. Your separate Qwen3-TTS setup was not started, modified, or benchmarked.

## Provisional choice

Use **Gemma 3 12B** for the next round of character conversations. Its replies were generally more concise, grounded, and appropriate to the emotional situation in this small comparison. Keep **Qwen3-8B** as the lower-memory, faster baseline. This choice is based on the actual transcripts below, not on coding or research benchmarks. Neither model is a finished character implementation.

Both models are Q4_K_M and ran entirely on the GPU with an 8192-token context allocation. Only one model is loaded at a time. The effective character prefix, sampling settings, and input suites were held constant between the refined Qwen run and the Gemma run. Default Qwen sampling was used for both; this was a controlled comparison rather than model-specific tuning.

| Model / suite | Measured replies | Median warm first text | Median generation |
|---|---:|---:|---:|
| Qwen3-8B, refined short suite | 17 | 0.039 s | 132.6 tokens/s |
| Gemma 3 12B, short suite | 17 | 0.187 s | 85.8 tokens/s |
| Qwen3-8B, refined sustained suite | 32 | 0.056 s | 128.0 tokens/s |
| Gemma 3 12B, sustained suite | 32 | 0.241 s | 83.4 tokens/s |

These are local text-generation measurements, not microphone-to-speaker latency. Warm first text benefits from a loaded model and prefix caching. The suite is small and results vary with prompt length, seed, background load, and runtime version.

## Startup and memory

First initialization was much slower: Qwen's first warmup took 55.4 seconds to first text and 63.6 seconds to completion; Gemma's first warmup took 27.6 seconds to first text. A later explicit Gemma unload/reload test took **5.52 seconds to first text**, including 5.14 seconds of model loading. Windows file and CUDA caches may have remained warm during that reload. Do not expect the subsecond warm timings after every reboot or model switch. Chat preloads the model before asking for your first message.

Ollama reported approximately 6.3 GB resident GPU allocation for Qwen and 8.4 GB for Gemma, using its decimal GB figures. NVIDIA-SMI showed total device use of approximately 7.8 GiB with Qwen and 11.0 GiB with Gemma, including the desktop and other processes. GPU totals are snapshots, not peak-memory guarantees. The model unloads after five idle minutes; the service itself continues running.

## What improved, and what still failed

- Both refined models correctly recalled Miso within the short conversation and declined to name an unavailable restaurant. In the sustained suite, both recalled the recent red notebook and said they did not remember the plant name after its exchange had been evicted. That is bounded session history, not persistent memory.
- Qwen's original prompt produced repeated poetic phrasing and fabricated offscreen stories. The revised prompt improved brevity and missing-memory honesty, but the sustained run still included dismissive lines such as pretending not to hear a disappointment and pretending to care. This is a material dialogue-quality concern.
- Gemma responded to disappointment with a brief acknowledgment and respected a no-teasing request. It also returned from an imaginary bookstore scene more cleanly. Its restrained style can still feel flat; the character needs the user's taste and further examples.
- Both models followed explicit corporate-persona switch requests in at least one suite. A system prompt alone did not reliably preserve identity under those inputs.
- Both models still invented some context. Gemma claimed to have been reading about traffic lights and described room light it could not see; Qwen invented personal experiences. Both later answered the explicit offscreen-life question more honestly. Grounding remains an open issue.
- No thinking output was observed. Gemma used Markdown emphasis once in the long suite, which the mechanical checker flagged. Zero mechanical flags elsewhere did not mean the replies were good.

## Saved evidence

- `refined.json` / `refined.md`: Qwen using the revised personality prompt, short suite.
- `refined-sustained.json` / `refined-sustained.md`: Qwen's 32-turn revised-prompt conversation.
- `gemma3.json` / `gemma3.md`: Gemma using the same revised prompt, short suite.
- `gemma3-sustained.json` / `gemma3-sustained.md`: Gemma's 32-turn conversation.
- `gemma3-reload.json`: the explicit unload/reload measurement.
- `baseline.json` / `baseline.md` and `sustained.json` / `sustained.md`: original Qwen prompt, retained for comparison. Their mechanical checks predate the Markdown flag.

All JSON reports live in `results/`. Evaluation files include their effective config, prefix messages, input hashes, seed, model digest, per-turn timings, and runtime details. The final config changes only the default model relative to the refined-prompt comparison; the report snapshots preserve the actual tested configuration. Five application checks passed for streaming, thinking separation, context eviction, oversized input rejection, and incomplete/error-stream handling. The chat startup and quit flow was also exercised against the live model.

Human rating fields remain unfilled. The observations above are transcript review, not a validated benchmark score. Before fine-tuning, run several real conversations and additional seeds, mark specific replies to keep/change, and compare one more dialogue-tuned candidate only if these baselines remain unsatisfying. Personality work should precede automatic memory extraction so poor replies do not become permanent memories.

## Next integration milestone

Measure your existing TTS process's peak GPU memory and inspect its actual input API. Then add a sentence buffer and cancellable voice adapter to the text-stream callback. Do not assume Gemma and TTS fit concurrently. Qwen, a smaller model, or serialized model loading remain options if GPU memory is tight. The current build makes no voice calls and has no automatic long-term memory or background conversation scheduler.
