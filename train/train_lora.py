from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import time
from pathlib import Path

import torch
import yaml
from torch.utils.data import DataLoader, Dataset

from recipe_qa.corpus.build import read_jsonl
from recipe_qa.training.dataset import split_template_holdout


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rss_mb() -> float:
    try:
        import psutil
    except ImportError:
        return 0.0
    return psutil.Process().memory_info().rss / (1024 * 1024)


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


class TokenizedDataset(Dataset):
    def __init__(self, examples: list[dict], tokenizer, max_seq_len: int) -> None:
        self.rows: list[dict] = []
        self.skipped = 0
        for example in examples:
            row = self._encode(example, tokenizer, max_seq_len)
            if row is None:
                self.skipped += 1
            else:
                self.rows.append(row)

    @staticmethod
    def _encode(example: dict, tokenizer, max_seq_len: int) -> dict | None:
        prompt_text = tokenizer.apply_chat_template(
            [{"role": "user", "content": example["prompt"]}],
            tokenize=False,
            add_generation_prompt=True,
        )
        prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
        eos = tokenizer.eos_token or ""
        target_ids = tokenizer(
            example["target_json"] + eos,
            add_special_tokens=False,
        )["input_ids"]
        if not target_ids or len(target_ids) >= max_seq_len:
            return None
        if len(prompt_ids) + len(target_ids) > max_seq_len:
            prompt_ids = prompt_ids[-(max_seq_len - len(target_ids)) :]
        input_ids = prompt_ids + target_ids
        labels = [-100] * len(prompt_ids) + target_ids
        return {
            "input_ids": input_ids,
            "attention_mask": [1] * len(input_ids),
            "labels": labels,
        }

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict:
        return self.rows[index]


def _collate(batch: list[dict], pad_token_id: int) -> dict:
    max_len = max(len(row["input_ids"]) for row in batch)
    input_ids = [
        row["input_ids"] + [pad_token_id] * (max_len - len(row["input_ids"]))
        for row in batch
    ]
    attention_mask = [
        row["attention_mask"] + [0] * (max_len - len(row["attention_mask"]))
        for row in batch
    ]
    labels = [
        row["labels"] + [-100] * (max_len - len(row["labels"]))
        for row in batch
    ]
    return {
        "input_ids": torch.tensor(input_ids, dtype=torch.long),
        "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
    }


def _split_examples(
    examples: list[dict],
    *,
    val_fraction: float,
    seed: int,
) -> tuple[list[dict], list[dict]]:
    if val_fraction <= 0:
        return examples, []
    doc_ids = sorted({example["source_doc_id"] for example in examples})
    rng = random.Random(seed)
    rng.shuffle(doc_ids)
    val_count = max(1, int(round(len(doc_ids) * val_fraction)))
    val_docs = set(doc_ids[:val_count])
    train = [row for row in examples if row["source_doc_id"] not in val_docs]
    val = [row for row in examples if row["source_doc_id"] in val_docs]
    return train, val


def _evaluate(model, loader: DataLoader) -> float:
    model.eval()
    total = 0.0
    steps = 0
    with torch.no_grad():
        for batch in loader:
            outputs = model(**batch)
            total += float(outputs.loss)
            steps += 1
    model.train()
    return total / steps if steps else 0.0


def _write_checksums(
    *,
    output_dir: Path,
    log_dir: Path,
    dataset_path: Path,
    config_path: Path,
) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            files[str(path.relative_to(output_dir))] = _sha256(path)
    lines = [f"{digest}  {name}" for name, digest in files.items()]
    lines.append(f"{_sha256(dataset_path)}  {dataset_path.name}")
    lines.append(f"{_sha256(config_path)}  {config_path.name}")
    (log_dir / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train a LoRA adapter on CPU.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("train/lora_config.yaml"),
    )
    parser.add_argument("--max-steps", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    if args.smoke:
        config["epochs"] = 1
        config["val_mode"] = "none"
        config["val_fraction"] = 0.0
        config["eval_every_steps"] = 0
        config["output_dir"] = "train/smoke_adapter"
        config["log_dir"] = "train/smoke_logs"
        args.limit = args.limit or 8
        args.max_steps = args.max_steps or 2

    seed = int(config.get("seed", 42))
    random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(int(config.get("threads", 8)))

    dataset_path = Path(config["dataset"])
    examples = list(read_jsonl(dataset_path))
    if args.limit:
        examples = examples[: args.limit]
    if not examples:
        raise SystemExit(f"no training examples in {dataset_path}")
    for example in examples:
        if example.get("split") != "train":
            raise SystemExit(f"non-train example: {example.get('example_id')}")
        if int(example.get("source_year") or 0) == 1824:
            raise SystemExit(f"OOD 1824 example: {example.get('example_id')}")

    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base_model = str(config["base_model"])
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    dtype = {
        "float32": torch.float32,
        "bfloat16": torch.bfloat16,
        "float16": torch.float16,
    }.get(str(config.get("dtype", "float32")), torch.float32)
    model = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype=dtype)
    model.config.use_cache = False
    if bool(config.get("gradient_checkpointing")):
        if hasattr(model, "activation_checkpointing_enable"):
            model.activation_checkpointing_enable()
        else:
            model.gradient_checkpointing_enable()

    lora = config["lora"]
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=int(lora["r"]),
        lora_alpha=int(lora["alpha"]),
        lora_dropout=float(lora["dropout"]),
        target_modules=list(lora["target_modules"]),
        bias="none",
    )
    model = get_peft_model(model, peft_config)
    if bool(config.get("gradient_checkpointing")):
        model.enable_input_require_grads()
    model.print_trainable_parameters()

    val_mode = str(config.get("val_mode", "doc"))
    val_templates: list[str] = []
    if val_mode == "template_holdout":
        train_examples, val_examples, val_templates = split_template_holdout(
            examples,
            seed=seed,
        )
    elif val_mode == "none":
        train_examples, val_examples = examples, []
    else:
        train_examples, val_examples = _split_examples(
            examples,
            val_fraction=float(config.get("val_fraction", 0.0)),
            seed=seed,
        )
    max_seq_len = int(config.get("max_seq_len", 768))
    train_dataset = TokenizedDataset(train_examples, tokenizer, max_seq_len)
    val_dataset = (
        TokenizedDataset(val_examples, tokenizer, max_seq_len)
        if val_examples
        else None
    )
    if len(train_dataset) == 0:
        raise SystemExit("no trainable examples after tokenization")

    batch_size = int(config.get("batch_size", 1))
    generator = torch.Generator().manual_seed(seed)
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
        generator=generator,
        collate_fn=lambda batch: _collate(batch, tokenizer.pad_token_id),
    )
    val_loader = (
        DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=0,
            collate_fn=lambda batch: _collate(batch, tokenizer.pad_token_id),
        )
        if val_dataset is not None and len(val_dataset) > 0
        else None
    )

    trainable = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.AdamW(
        trainable,
        lr=float(config.get("learning_rate", 2e-4)),
        weight_decay=float(config.get("weight_decay", 0.0)),
    )
    grad_accum = max(1, int(config.get("grad_accum", 1)))
    epochs = max(1, int(config.get("epochs", 1)))
    steps_per_epoch = math.ceil(len(train_loader) / grad_accum)
    total_steps = args.max_steps or steps_per_epoch * epochs
    total_steps = max(1, total_steps)
    warmup_steps = max(1, int(total_steps * float(config.get("warmup_ratio", 0.0))))

    def lr_lambda(step: int) -> float:
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        return max(0.0, 1.0 - progress)

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    max_grad_norm = float(config.get("max_grad_norm", 1.0))
    eval_every = int(config.get("eval_every_steps", 0))
    log_every = max(1, int(config.get("log_every_steps", 1)))

    output_dir = Path(config["output_dir"])
    log_dir = Path(config["log_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    loss_path = log_dir / "loss.jsonl"
    eval_path = log_dir / "eval.jsonl"
    if loss_path.exists():
        loss_path.unlink()
    if eval_path.exists():
        eval_path.unlink()

    start = time.perf_counter()
    peak_rss = _rss_mb()
    global_step = 0
    model.train()
    optimizer.zero_grad()
    stop = False
    for epoch in range(1, epochs + 1):
        for step, batch in enumerate(train_loader, start=1):
            outputs = model(**batch)
            loss = outputs.loss
            (loss / grad_accum).backward()
            if step % grad_accum == 0 or step == len(train_loader):
                torch.nn.utils.clip_grad_norm_(trainable, max_grad_norm)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                global_step += 1
                rss = _rss_mb()
                peak_rss = max(peak_rss, rss)
                if global_step == 1 or global_step % log_every == 0:
                    _append_jsonl(
                        loss_path,
                        {
                            "step": global_step,
                            "epoch": epoch,
                            "loss": float(loss.detach()),
                            "lr": optimizer.param_groups[0]["lr"],
                            "elapsed_s": round(time.perf_counter() - start, 2),
                            "rss_mb": round(rss, 1),
                        },
                    )
                if eval_every and val_loader is not None and global_step % eval_every == 0:
                    eval_loss = _evaluate(model, val_loader)
                    _append_jsonl(
                        eval_path,
                        {
                            "step": global_step,
                            "eval_loss": eval_loss,
                            "elapsed_s": round(time.perf_counter() - start, 2),
                            "rss_mb": round(_rss_mb(), 1),
                        },
                    )
                    model.train()
                if args.max_steps and global_step >= args.max_steps:
                    stop = True
                    break
        if stop:
            break

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    wall_time = time.perf_counter() - start
    adapter_files = _write_checksums(
        output_dir=output_dir,
        log_dir=log_dir,
        dataset_path=dataset_path,
        config_path=args.config,
    )
    trainable_params = sum(
        parameter.numel() for parameter in model.parameters() if parameter.requires_grad
    )
    total_params = sum(parameter.numel() for parameter in model.parameters())
    resource = {
        "base_model": base_model,
        "dataset": str(dataset_path),
        "dataset_sha256": _sha256(dataset_path),
        "adapter_dir": str(output_dir),
        "log_dir": str(log_dir),
        "wall_time_s": round(wall_time, 2),
        "peak_rss_mb": round(peak_rss, 1),
        "torch_threads": torch.get_num_threads(),
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "epochs": epochs,
        "global_steps": global_step,
        "val_mode": val_mode,
        "val_templates": val_templates,
        "train_examples": len(train_dataset),
        "val_examples": len(val_dataset) if val_dataset is not None else 0,
        "skipped_examples": train_dataset.skipped
        + (val_dataset.skipped if val_dataset is not None else 0),
        "trainable_params": trainable_params,
        "total_params": total_params,
        "adapter_files": adapter_files,
    }
    (log_dir / "resource.json").write_text(
        json.dumps(resource, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (log_dir / "training_args.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(resource, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
