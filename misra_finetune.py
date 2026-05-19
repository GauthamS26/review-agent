#!/usr/bin/env python3
"""
Simple Llama Fine-Tuning for MISRA C Code Review
=================================================
Method: Supervised Fine-Tuning (SFT) — top-layer-only training.
  - No LoRA, no QLoRA, no adapter layers.
  - Freezes embeddings + bottom transformer layers.
  - Trains only the top N decoder layers + final LayerNorm + LM head.
  - Works on CPU or a single low-VRAM GPU (≥ 4 GB).
  - Uses TinyLlama-1.1B-Chat (default) — swap via --model for other sizes.

Usage
-----
  python misra_finetune.py                          # default settings
  python misra_finetune.py --model TinyLlama/TinyLlama-1.1B-Chat-v1.0
  python misra_finetune.py --epochs 3 --train_layers 4
  python misra_finetune.py --infer --prompt "Review this C code for MISRA violations: int x; x = x + 1;"
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ── optional: silence tokenizer parallelism warnings ──────────────────────────
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# ── imports (fail-fast with a helpful message) ─────────────────────────────────
try:
    import torch
    from torch.utils.data import Dataset, DataLoader
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        get_linear_schedule_with_warmup,
    )
except ImportError as exc:
    sys.exit(
        f"[ERROR] Missing dependency: {exc}\n"
        "Run:  pip install torch transformers datasets accelerate\n"
    )

# ── defaults ──────────────────────────────────────────────────────────────────
DEFAULT_MODEL      = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
DEFAULT_OUTPUT_DIR = "misra_finetuned"
DEFAULT_DATA_FILE  = "misra_train.json"
MAX_SEQ_LEN        = 512          # keep short to stay within CPU memory
DEFAULT_EPOCHS     = 2
DEFAULT_BATCH      = 1            # micro-batch on CPU
GRAD_ACCUM_STEPS   = 4            # simulate batch of 4
DEFAULT_LR         = 2e-5
DEFAULT_TRAIN_LAYERS = 2          # how many top decoder layers to unfreeze


# ══════════════════════════════════════════════════════════════════════════════
# Dataset
# ══════════════════════════════════════════════════════════════════════════════

class MISRADataset(Dataset):
    """Tokenised MISRA instruction-tuning dataset."""

    def __init__(self, data_file: str, tokenizer, max_len: int = MAX_SEQ_LEN):
        self.tokenizer = tokenizer
        self.max_len   = max_len
        self.samples   = self._load(data_file)

    # ------------------------------------------------------------------
    def _load(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)
        return [r["text"] for r in records]

    # ------------------------------------------------------------------
    def __len__(self):
        return len(self.samples)

    # ------------------------------------------------------------------
    def __getitem__(self, idx):
        text = self.samples[idx]
        enc  = self.tokenizer(
            text,
            max_length=self.max_len,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )
        input_ids      = enc["input_ids"].squeeze(0)
        attention_mask = enc["attention_mask"].squeeze(0)
        # For causal LM, labels == input_ids; pad positions → -100 (ignored)
        labels = input_ids.clone()
        labels[attention_mask == 0] = -100
        return {
            "input_ids":      input_ids,
            "attention_mask": attention_mask,
            "labels":         labels,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Freeze / Unfreeze helpers
# ══════════════════════════════════════════════════════════════════════════════

def freeze_bottom_layers(model, num_trainable_top_layers: int) -> int:
    """
    Freeze everything except:
      • the top `num_trainable_top_layers` decoder layers
      • the final layer norm
      • the LM head (lm_head / embed_out)
    Returns the count of trainable parameters.
    """
    # First freeze all parameters
    for param in model.parameters():
        param.requires_grad = False

    # Locate the list of decoder layers (works for LLaMA / TinyLlama / Mistral)
    decoder_layers = None
    for attr in ("model.layers", "transformer.h", "model.decoder.layers"):
        try:
            obj = model
            for part in attr.split("."):
                obj = getattr(obj, part)
            decoder_layers = obj
            break
        except AttributeError:
            continue

    if decoder_layers is None:
        # Fallback: unfreeze everything (small models are fine)
        print("[warn] Could not locate decoder layers — training all parameters.")
        for param in model.parameters():
            param.requires_grad = True
    else:
        total = len(decoder_layers)
        start = max(0, total - num_trainable_top_layers)
        print(f"[freeze] {total} decoder layers total — "
              f"freezing layers 0–{start-1}, training layers {start}–{total-1}.")
        for layer in decoder_layers[start:]:
            for param in layer.parameters():
                param.requires_grad = True

        # Always train the final norm + lm_head
        for attr in ("model.norm", "transformer.ln_f", "model.final_layernorm",
                     "lm_head", "embed_out"):
            try:
                obj = model
                for part in attr.split("."):
                    obj = getattr(obj, part)
                for param in obj.parameters():
                    param.requires_grad = True
            except AttributeError:
                pass

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_p   = sum(p.numel() for p in model.parameters())
    print(f"[params] Trainable: {trainable:,} / {total_p:,} "
          f"({100.0 * trainable / total_p:.2f}%)")
    return trainable


# ══════════════════════════════════════════════════════════════════════════════
# Training loop
# ══════════════════════════════════════════════════════════════════════════════

def train(args):
    # ── 1. Build / verify dataset ──────────────────────────────────────────
    data_path = Path(args.data_file)
    if not data_path.exists():
        print(f"[data] {data_path} not found — generating from misra_dataset.py …")
        try:
            import misra_dataset
            misra_dataset.build_dataset(str(data_path))
        except ImportError:
            sys.exit("[ERROR] misra_dataset.py not found. Run it first.")

    # ── 2. Load tokenizer ─────────────────────────────────────────────────
    print(f"[load] Tokenizer: {args.model}")
    tokenizer = AutoTokenizer.from_pretrained(
        args.model, use_fast=True, trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ── 3. Load model in float32 (CPU-safe) ───────────────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[load] Model: {args.model}  →  device: {device}")

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        dtype=torch.float32,          # float32 for CPU compatibility
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    model.to(device)

    # ── 4. Freeze lower layers ────────────────────────────────────────────
    freeze_bottom_layers(model, args.train_layers)

    # ── 5. Dataset + DataLoader ───────────────────────────────────────────
    dataset    = MISRADataset(str(data_path), tokenizer, args.max_seq_len)
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    print(f"[data] {len(dataset)} training samples loaded.")

    # ── 6. Optimiser + scheduler ──────────────────────────────────────────
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable_params, lr=args.lr, weight_decay=0.01)

    total_steps  = (len(dataloader) // GRAD_ACCUM_STEPS) * args.epochs
    warmup_steps = max(1, total_steps // 10)
    scheduler    = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
    )

    # ── 7. Training loop ──────────────────────────────────────────────────
    # Maximise CPU parallelism
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    torch.set_num_threads(cpu_count)
    print(f"[cpu] Using {cpu_count} threads")

    print(f"\n[train] Starting: {args.epochs} epoch(s), "
          f"batch={args.batch_size}, grad_accum={GRAD_ACCUM_STEPS}, lr={args.lr}")

    model.train()
    global_step  = 0
    epoch_losses = []
    optimizer.zero_grad()

    for epoch in range(1, args.epochs + 1):
        epoch_loss = 0.0
        for step, batch in enumerate(dataloader, start=1):
            input_ids      = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels         = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = outputs.loss / GRAD_ACCUM_STEPS
            loss.backward()
            epoch_loss += outputs.loss.item()

            if step % GRAD_ACCUM_STEPS == 0 or step == len(dataloader):
                torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                global_step += 1

                avg = epoch_loss / step
                print(f"  epoch {epoch}/{args.epochs}  "
                      f"step {global_step}  "
                      f"loss {avg:.4f}")

        avg_epoch = epoch_loss / len(dataloader)
        epoch_losses.append(round(avg_epoch, 6))
        print(f"[epoch {epoch}] avg loss: {avg_epoch:.4f}")

    # ── 8. Save ───────────────────────────────────────────────────────────
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Use PyTorch .bin format with sharding to avoid peak-RAM OOM on CPU.
    # safetensors serialisation requires all tensors contiguous in RAM at once
    # (4.4 GB for a 1.1B float32 model), which causes MemoryError on low-RAM machines.
    print("[save] Writing sharded PyTorch checkpoints (500 MB per shard) …")
    model.save_pretrained(
        str(out_dir),
        safe_serialization=False,   # write .bin, not .safetensors
        max_shard_size="500MB",     # split into chunks to reduce peak RAM
    )
    tokenizer.save_pretrained(str(out_dir))
    print(f"\n[save] Fine-tuned model saved → {out_dir.resolve()}")

    # ── 9. Write DVC metrics ──────────────────────────────────────────────
    metrics = {
        "final_loss":    epoch_losses[-1],
        "epoch_losses":  epoch_losses,
        "epochs":        args.epochs,
        "train_layers":  args.train_layers,
        "max_seq_len":   args.max_seq_len,
        "trainable_params": sum(p.numel() for p in model.parameters() if p.requires_grad),
        "total_params":     sum(p.numel() for p in model.parameters()),
    }
    metrics_path = Path("training_metrics.json")
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"[metrics] Saved → {metrics_path.resolve()}")

    _write_ollama_modelfile(str(out_dir))


# ══════════════════════════════════════════════════════════════════════════════
# Inference (quick test after training)
# ══════════════════════════════════════════════════════════════════════════════

def infer(args):
    """Load the saved model and answer a single MISRA review prompt."""
    model_path = Path(args.output_dir)
    if not model_path.exists():
        sys.exit(f"[ERROR] Trained model not found at {model_path}. Run training first.")

    print(f"[infer] Loading model from {model_path} …")
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model  = AutoModelForCausalLM.from_pretrained(
        str(model_path), torch_dtype=torch.float32
    ).to(device)
    model.eval()

    prompt = (
        f"### Instruction:\nReview the following C code for MISRA C:2012 violations.\n\n"
        f"### Input:\n{args.prompt}\n\n"
        f"### Response:\n"
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,          # greedy decoding — deterministic
            temperature=1.0,
            repetition_penalty=1.1,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )

    generated = tokenizer.decode(
        output_ids[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True
    )
    print("\n" + "=" * 70)
    print("MISRA Code Review Result")
    print("=" * 70)
    print(generated.strip())
    print("=" * 70)


# ══════════════════════════════════════════════════════════════════════════════
# Ollama Modelfile export
# ══════════════════════════════════════════════════════════════════════════════

def _write_ollama_modelfile(output_dir: str) -> None:
    """Write an Ollama Modelfile so the fine-tuned weights can be served locally."""
    modelfile = (
        "# Ollama Modelfile — MISRA C:2012 Code Review Expert\n"
        "# Usage after training:\n"
        "#   ollama create misra-reviewer -f Modelfile\n"
        "#   ollama run misra-reviewer\n\n"
        f'FROM {Path(output_dir).resolve()}\n\n'
        'PARAMETER temperature 0.2\n'
        'PARAMETER top_p 0.9\n'
        'PARAMETER repeat_penalty 1.1\n\n'
        'SYSTEM """\n'
        "You are an expert MISRA C:2012 code review assistant for safety-critical "
        "embedded systems. When given C source code, you identify all MISRA C:2012 "
        "violations (Mandatory, Required, and Advisory), state the rule number and "
        "category, quote the offending line, explain why it violates the rule, and "
        "provide a concrete fix. If no violations exist, confirm compliance.\n"
        '"""\n\n'
        'TEMPLATE """{{ if .System }}<|system|>\n'
        '{{ .System }}</s>\n'
        '{{ end }}{{ if .Prompt }}<|user|>\n'
        '{{ .Prompt }}</s>\n'
        '<|assistant|>\n'
        '{{ end }}{{ .Response }}<EOT>\n"""\n'
    )
    mf_path = Path(output_dir) / "Modelfile"
    mf_path.write_text(modelfile, encoding="utf-8")
    print(f"[ollama] Modelfile written → {mf_path.resolve()}")
    print("[ollama] To serve locally:")
    print(f"         ollama create misra-reviewer -f {mf_path.resolve()}")
    print("         ollama run misra-reviewer")


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Simple Llama fine-tuning for MISRA C:2012 code review "
                    "(top-layer SFT, no LoRA, no quantisation)."
    )
    p.add_argument("--model",        default=DEFAULT_MODEL,
                   help=f"HuggingFace model ID or local path. Default: {DEFAULT_MODEL}")
    p.add_argument("--data_file",    default=DEFAULT_DATA_FILE,
                   help="Path to MISRA training JSON (auto-generated if missing).")
    p.add_argument("--output_dir",   default=DEFAULT_OUTPUT_DIR,
                   help="Directory to save the fine-tuned model.")
    p.add_argument("--epochs",       type=int,   default=DEFAULT_EPOCHS)
    p.add_argument("--batch_size",   type=int,   default=DEFAULT_BATCH)
    p.add_argument("--lr",           type=float, default=DEFAULT_LR)
    p.add_argument("--train_layers", type=int,   default=DEFAULT_TRAIN_LAYERS,
                   help="Number of top decoder layers to train (rest are frozen).")
    p.add_argument("--max_seq_len",  type=int,   default=MAX_SEQ_LEN)
    p.add_argument("--infer",        action="store_true",
                   help="Run inference on --prompt instead of training.")
    p.add_argument("--prompt",       default="int x; x = x + 1;",
                   help="C code snippet to review (used with --infer).")
    return p


def main():
    args = build_parser().parse_args()
    if args.infer:
        infer(args)
    else:
        train(args)


if __name__ == "__main__":
    main()
