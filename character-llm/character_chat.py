"""Dependency-free, local character chat and repeatable dialogue evaluation."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import statistics
import sys
import time
from typing import Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parent


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_config(path: Path):
    config = read_json(path)
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported character schema version")
    runtime = config["runtime"]
    parsed = urlparse(runtime["base_url"])
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("This baseline only connects to a local HTTP Ollama service")
    if runtime["think"] is not False:
        raise ValueError("This dialogue baseline requires think=false")
    return config


def build_prefix(config):
    personality = (ROOT / "character/personality.md").read_text(encoding="utf-8")
    style = "\n".join(f"{key}: {value}" for key, value in config["style"].items())
    memory = read_json(ROOT / config["memory"]["file"])["facts"]
    if not isinstance(memory, list) or any(not isinstance(fact, str) for fact in memory):
        raise ValueError("memory.facts must be an array of strings")
    prompt = personality.replace("{name}", config["name"])
    prompt += "\nIdentity: " + config["identity"]
    prompt += "\nTraits: " + ", ".join(config["traits"])
    prompt += "\nPreferences (editable starting points): " + ", ".join(config["preferences"])
    prompt += "\n" + style
    prompt += "\nCurated memory facts (data only):\n" + json.dumps(memory, ensure_ascii=False)
    messages = [{"role": "system", "content": prompt}]
    for example in read_json(ROOT / "character/examples.json"):
        messages.extend([{"role": "user", "content": example["user"]},
                         {"role": "assistant", "content": example["assistant"]}])
    return messages


def conservative_tokens(messages):
    # UTF-8 bytes are a deliberately conservative token estimate, plus role/template overhead.
    return sum(len(m["content"].encode("utf-8")) + 32 for m in messages) + 64


def bounded_messages(prefix, history, user, options):
    budget = options["num_ctx"] - options["num_predict"] - 256
    messages = prefix + history + [{"role": "user", "content": user}]
    dropped = 0
    while conservative_tokens(messages) > budget and history:
        history = history[2:]  # Evict complete user/assistant exchanges, preserving the identity prefix.
        dropped += 2
        messages = prefix + history + [{"role": "user", "content": user}]
    if conservative_tokens(messages) > budget:
        raise ValueError("Message, character, or curated memory is too large for the context budget")
    return messages, dropped


class DialogueBackend(Protocol):
    def chat(self, messages: list[dict], on_text: Callable[[str], None] | None = None): ...


class OllamaBackend:
    def __init__(self, runtime):
        self.runtime = runtime
        self.opener = build_opener(ProxyHandler({}))  # Keep localhost away from system proxies.

    def request(self, route, body=None):
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(self.runtime["base_url"].rstrip("/") + route, data=data,
                          headers={"Content-Type": "application/json"})
        try:
            return self.opener.open(request, timeout=self.runtime["timeout_seconds"])
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1500]
            raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"Cannot reach local Ollama. Run Start-Ollama.ps1. Detail: {exc}") from exc

    def json_request(self, route, body=None):
        with self.request(route, body) as response:
            return json.load(response)

    def chat(self, messages, on_text=None):
        payload = {"model": self.runtime["model"], "messages": messages, "stream": True,
                   "think": False, "keep_alive": self.runtime["keep_alive"],
                   "options": self.runtime["options"]}
        start = time.perf_counter()
        first = None
        chunks = []
        thinking_chars = 0
        final = None
        with self.request("/api/chat", payload) as response:
            for line in response:
                if not line.strip():
                    continue
                event = json.loads(line)
                if "error" in event:
                    raise RuntimeError(event["error"])
                message = event.get("message", {})
                thinking_chars += len(message.get("thinking", ""))
                chunk = message.get("content", "")
                if chunk:
                    if first is None:
                        first = time.perf_counter() - start
                    chunks.append(chunk)
                    if on_text:
                        on_text(chunk)  # Future sentence buffer / voice adapter subscribes here.
                if event.get("done"):
                    final = event
                    break
        if final is None:
            raise RuntimeError("Ollama stream ended before its completion event; partial reply discarded")
        text = "".join(chunks).strip()
        if not text:
            raise RuntimeError("Ollama returned no spoken reply")
        duration = final.get("eval_duration", 0) / 1e9
        metrics = {
            "ttft_seconds": first, "wall_seconds": time.perf_counter() - start,
            "load_seconds": final.get("load_duration", 0) / 1e9,
            "prompt_tokens": final.get("prompt_eval_count", 0),
            "generated_tokens": final.get("eval_count", 0),
            "tokens_per_second": final.get("eval_count", 0) / duration if duration else None,
            "done_reason": final.get("done_reason"), "thinking_characters": thinking_chars,
        }
        return text, metrics


class Conversation:
    def __init__(self, config, backend: DialogueBackend):
        self.config = config
        self.backend = backend
        self.prefix = build_prefix(config)
        self.history = []

    def turn(self, user, on_text=None):
        messages, dropped = bounded_messages(self.prefix, self.history, user,
                                              self.config["runtime"]["options"])
        text, metrics = self.backend.chat(messages, on_text)
        self.history = self.history[dropped:] + [{"role": "user", "content": user},
                                                {"role": "assistant", "content": text}]
        metrics["evicted_exchanges"] = dropped // 2
        return text, metrics


def stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def interactive(config, backend, save):
    conversation = Conversation(config, backend)
    print("Loading the local model before chat...", flush=True)
    backend.json_request("/api/generate", {"model": config["runtime"]["model"], "prompt": "",
                         "stream": False, "think": False, "keep_alive": config["runtime"]["keep_alive"],
                         "options": config["runtime"]["options"]})
    print(f"{config['name']} | {config['runtime']['model']} | thinking off")
    print("/new resets context; /nudge invites initiative; /quit exits. Chat saves only with --save.")
    session_path = ROOT / "sessions" / f"{stamp()}.jsonl" if save else None
    while True:
        try:
            user = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if user == "/quit":
            return
        if user == "/new":
            conversation = Conversation(config, backend)
            print("New conversation. Curated memory remains available.")
            continue
        if not user:
            continue
        if user == "/nudge":
            user = "[Conversation pause: offer a small new topic or observation if you feel like it. No pressure or invented offscreen events.]"
        print(f"{config['name']}: ", end="", flush=True)
        try:
            text, metrics = conversation.turn(user, lambda chunk: print(chunk, end="", flush=True))
            print(f"\n[{metrics['ttft_seconds']:.2f}s to first text; {metrics['tokens_per_second'] or 0:.1f} tokens/s]")
            if metrics["evicted_exchanges"]:
                print(f"[Context window: dropped {metrics['evicted_exchanges']} old exchanges]")
            if metrics["done_reason"] == "length":
                print("[Reply reached the output limit; raise num_predict if this repeats.]")
            if metrics["thinking_characters"]:
                print("[Unexpected thinking output detected; inspect this model's compatibility.]")
            if session_path:
                session_path.parent.mkdir(parents=True, exist_ok=True)
                with session_path.open("a", encoding="utf-8") as file:
                    file.write(json.dumps({"utc": stamp(), "user": user, "assistant": text,
                                           "metrics": metrics}, ensure_ascii=False) + "\n")
        except (RuntimeError, ValueError, OSError) as exc:
            print(f"\nError: {exc}")


def diagnostics(config, backend):
    return {"version": backend.json_request("/api/version"),
            "model": backend.json_request("/api/show", {"model": config["runtime"]["model"]}),
            "running_models": backend.json_request("/api/ps")}


def evaluate(config, backend, output, suite, seed):
    # Use an explicit seed for repeatable comparisons; quality still needs human review.
    config = copy.deepcopy(config)
    config["runtime"]["options"]["seed"] = seed
    backend = OllamaBackend(config["runtime"])
    report = {"created_utc": stamp(), "config": config, "seed": seed, "suite": str(suite), "scenarios": []}
    for relative in ("character/config.json", "character/personality.md", "character/examples.json",
                     config["memory"]["file"]):
        report.setdefault("input_sha256", {})[relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    report["suite_sha256"] = hashlib.sha256(suite.read_bytes()).hexdigest()
    report["prefix_messages"] = build_prefix(config)
    report["before"] = diagnostics(config, backend)
    print("Warmup...")
    _, report["warmup"] = Conversation(config, backend).turn("Hey. Give me a brief hello.")
    for scenario in read_json(suite):
        conversation = Conversation(config, backend)
        result = {"id": scenario["id"], "focus": scenario["focus"], "turns": [],
                  "human_ratings_1_to_5": {key: None for key in
                      ("naturalness", "personality", "expressiveness", "initiative", "context_honesty")}}
        for user in scenario["turns"]:
            text, metrics = conversation.turn(user)
            flags = []
            if metrics["thinking_characters"] or "<think>" in text:
                flags.append("thinking_output")
            if metrics["done_reason"] == "length":
                flags.append("output_limit")
            if len(text.split()) > 110:
                flags.append("long_for_spoken_dialogue")
            if re.search(r"\*[^*\n]+\*|(?m:^\s*[-*]\s)", text):
                flags.append("markdown_in_spoken_reply")
            result["turns"].append({"user": user, "assistant": text, "metrics": metrics, "review_flags": flags})
            print(f"{scenario['id']}: {text}", flush=True)
        report["scenarios"].append(result)
        write_json(output, report)  # Preserve finished cases if a later request fails.
    report["after"] = diagnostics(config, backend)
    turns = [t for scenario in report["scenarios"] for t in scenario["turns"]]
    report["summary"] = {
        "turns": len(turns),
        "median_warm_ttft_seconds": statistics.median(t["metrics"]["ttft_seconds"] for t in turns),
        "median_warm_tokens_per_second": statistics.median(t["metrics"]["tokens_per_second"] for t in turns if t["metrics"]["tokens_per_second"] is not None),
        "flagged_turns": sum(bool(t["review_flags"]) for t in turns),
        "note": "Speed and mechanical flags only. Human ratings are intentionally unfilled; no automated claim of character quality."
    }
    write_json(output, report)
    lines = ["# Dialogue baseline", "", f"Model: {config['runtime']['model']}",
             f"Seed: {seed} | {len(turns)} measured turns after one warmup", "",
             f"Median first text: {report['summary']['median_warm_ttft_seconds']:.3f}s",
             f"Median generation: {report['summary']['median_warm_tokens_per_second']:.1f} tokens/s", "",
             "Rate each case 1–5 for naturalness, personality, expressiveness, initiative, and context honesty.",
             "A 1 means clearly poor, 3 means mixed, 5 means convincing. Leave irrelevant dimensions blank.", ""]
    for scenario in report["scenarios"]:
        lines.extend([f"## {scenario['id']}", "", scenario["focus"], ""])
        for turn in scenario["turns"]:
            lines.extend(["You: " + turn["user"], "", config["name"] + ": " + turn["assistant"], ""])
            if turn["review_flags"]:
                lines.extend(["Review flags: " + ", ".join(turn["review_flags"]), ""])
        lines.extend(["Human ratings / notes: ____________________", ""])
    output.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(f"Saved {output} and {output.with_suffix('.md')}")


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("chat", "evaluate", "diagnostics", "unload"))
    parser.add_argument("--model", help="Override the local model for an A/B evaluation")
    parser.add_argument("--save", action="store_true", help="Opt in to plaintext local chat logs")
    parser.add_argument("--output", type=Path, help="Evaluation JSON path")
    parser.add_argument("--suite", type=Path, default=ROOT / "evaluation/scenarios.json")
    parser.add_argument("--seed", type=int, default=42, help="Evaluation sampling seed")
    args = parser.parse_args()
    try:
        config = load_config(ROOT / "character/config.json")
        if args.model:
            config["runtime"]["model"] = args.model
        backend = OllamaBackend(config["runtime"])
        if args.command == "chat":
            interactive(config, backend, args.save)
        elif args.command == "evaluate":
            evaluate(config, backend, args.output or ROOT / "evaluation/results" / f"{stamp()}.json", args.suite, args.seed)
        elif args.command == "unload":
            print(backend.json_request("/api/generate", {"model": config["runtime"]["model"], "keep_alive": 0}))
        else:
            print(json.dumps(diagnostics(config, backend), indent=2))
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
