"""MedGemma QLoRA fine-tuning pipeline.

Fine-tunes MedGemma 4B IT on SCIN dermatology data using QLoRA
(4-bit quantized LoRA) for improved SOAP note generation.

VRAM budget on RTX 3090 (24GB):
  - MedGemma 4B at 4-bit: ~3GB
  - LoRA adapters: ~2GB
  - Training overhead: ~5GB
  Total: ~10GB (fits comfortably)

Covers: REQ-MOD-001, REQ-MOD-002
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import structlog
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)

from src.utils.config import settings

logger = structlog.get_logger(__name__)

# Default LoRA configuration
DEFAULT_LORA_R = 16
DEFAULT_LORA_ALPHA = 32
DEFAULT_LORA_DROPOUT = 0.05
DEFAULT_TARGET_MODULES = ["q_proj", "v_proj", "k_proj", "o_proj"]

# Default training configuration
DEFAULT_EPOCHS = 3
DEFAULT_LR = 2e-4
DEFAULT_BATCH_SIZE = 4
DEFAULT_GRAD_ACCUM = 4
DEFAULT_MAX_SEQ_LEN = 1024


def load_jsonl(path: Path) -> list[dict[str, str]]:
    """Load a JSONL file into a list of dicts."""
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _format_instruction(example: dict[str, str]) -> str:
    """Format a single example as an instruction-following prompt."""
    return (
        "<start_of_turn>user\n"
        "You are a dermatological triage assistant. Generate a SOAP note for the following case.\n"
        "This is an AI-assisted triage assessment, NOT a diagnosis. "
        "Always recommend seeking professional medical help.\n\n"
        f"{example['input']}\n"
        "<end_of_turn>\n"
        "<start_of_turn>model\n"
        f"{example['output']}\n"
        "<end_of_turn>"
    )


def create_bnb_config() -> BitsAndBytesConfig:
    """Create 4-bit quantization config for QLoRA."""
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )


def load_base_model(
    model_id: str = "",
    device: str = "auto",
) -> tuple[Any, Any]:
    """Load MedGemma base model with 4-bit quantization.

    Args:
        model_id: HuggingFace model ID. Defaults to settings.
        device: Device string. Defaults to settings.

    Returns:
        Tuple of (model, tokenizer).
    """
    model_id = model_id or settings.llm.medgemma_model_id
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info("loading_base_model_for_finetune", model_id=model_id, device=device)
    t0 = time.monotonic()

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = create_bnb_config() if device == "cuda" else None

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map=device if device == "cuda" else None,
        torch_dtype=torch.bfloat16,
    )

    elapsed = int((time.monotonic() - t0) * 1000)
    logger.info("base_model_loaded", model_id=model_id, load_ms=elapsed)
    return model, tokenizer


def apply_lora(
    model: Any,
    r: int = DEFAULT_LORA_R,
    alpha: int = DEFAULT_LORA_ALPHA,
    dropout: float = DEFAULT_LORA_DROPOUT,
    target_modules: list[str] | None = None,
) -> Any:
    """Apply LoRA adapters to the model.

    Args:
        model: Base model (quantized or not).
        r: LoRA rank.
        alpha: LoRA alpha scaling.
        dropout: LoRA dropout.
        target_modules: Which modules to adapt.

    Returns:
        Model with LoRA adapters applied.
    """
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    if target_modules is None:
        target_modules = DEFAULT_TARGET_MODULES

    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=r,
        lora_alpha=alpha,
        lora_dropout=dropout,
        target_modules=target_modules,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)

    trainable, total = model.get_nb_trainable_parameters()
    logger.info(
        "lora_applied",
        r=r,
        alpha=alpha,
        target_modules=target_modules,
        trainable_params=trainable,
        total_params=total,
        trainable_pct=f"{trainable / total * 100:.2f}%",
    )
    return model


def run_training(
    model: Any,
    tokenizer: Any,
    train_data: list[dict[str, str]],
    val_data: list[dict[str, str]],
    output_dir: str = "models/medgemma-lora-derm",
    epochs: int = DEFAULT_EPOCHS,
    lr: float = DEFAULT_LR,
    batch_size: int = DEFAULT_BATCH_SIZE,
    grad_accum: int = DEFAULT_GRAD_ACCUM,
    max_seq_len: int = DEFAULT_MAX_SEQ_LEN,
) -> Path:
    """Run QLoRA fine-tuning with SFTTrainer.

    Args:
        model: Model with LoRA adapters.
        tokenizer: Tokenizer.
        train_data: Training examples with "input" and "output" keys.
        val_data: Validation examples.
        output_dir: Where to save LoRA adapters.
        epochs: Number of training epochs.
        lr: Learning rate.
        batch_size: Per-device batch size.
        grad_accum: Gradient accumulation steps.
        max_seq_len: Maximum sequence length.

    Returns:
        Path to saved LoRA adapters.
    """
    from datasets import Dataset

    logger.info(
        "starting_finetune",
        train_examples=len(train_data),
        val_examples=len(val_data),
        epochs=epochs,
        lr=lr,
        batch_size=batch_size,
        grad_accum=grad_accum,
        effective_batch_size=batch_size * grad_accum,
    )

    train_texts = [_format_instruction(ex) for ex in train_data]
    val_texts = [_format_instruction(ex) for ex in val_data]

    # Gemma 3 / MedGemma requires token_type_ids during training.
    # Pre-tokenize with token_type_ids so the trainer doesn't hit the
    # ValueError from modeling_gemma3.py.
    def _tokenize_batch(texts: list[str]) -> dict[str, Any]:
        encoded = tokenizer(
            texts,
            truncation=True,
            max_length=max_seq_len,
            padding="max_length",
            return_tensors=None,
        )
        # Add token_type_ids if the tokenizer didn't produce them
        if "token_type_ids" not in encoded:
            encoded["token_type_ids"] = [[0] * len(ids) for ids in encoded["input_ids"]]
        # Labels = input_ids (causal LM); mask padding with -100
        encoded["labels"] = [
            [tok if tok != tokenizer.pad_token_id else -100 for tok in ids]
            for ids in encoded["input_ids"]
        ]
        return dict(encoded)

    train_enc = _tokenize_batch(train_texts)
    val_enc = _tokenize_batch(val_texts)

    train_dataset = Dataset.from_dict(train_enc)
    val_dataset = Dataset.from_dict(val_enc)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_path),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=lr,
        weight_decay=0.01,
        warmup_ratio=0.1,
        lr_scheduler_type="cosine",
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        bf16=torch.cuda.is_available(),
        gradient_checkpointing=True,
        report_to="none",
        remove_unused_columns=False,
    )

    t0 = time.monotonic()

    from transformers import Trainer

    trainer = Trainer(
        model=model,
        processing_class=tokenizer,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
    )

    trainer.train()
    elapsed = int((time.monotonic() - t0) * 1000)

    # Save LoRA adapters only (not the full model)
    adapter_path = output_path / "adapter"
    model.save_pretrained(str(adapter_path))
    tokenizer.save_pretrained(str(adapter_path))

    logger.info(
        "finetune_complete",
        output_dir=str(adapter_path),
        training_ms=elapsed,
        epochs=epochs,
    )
    return adapter_path


def main() -> None:
    """CLI entry point for MedGemma QLoRA fine-tuning."""
    import argparse

    from src.utils.logger import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(description="Fine-tune MedGemma with QLoRA on SCIN data")
    parser.add_argument(
        "--train-data",
        default="data/processed/finetune/train.jsonl",
        help="Path to training JSONL",
    )
    parser.add_argument(
        "--val-data",
        default="data/processed/finetune/val.jsonl",
        help="Path to validation JSONL",
    )
    parser.add_argument(
        "--output-dir",
        default="models/medgemma-lora-derm",
        help="Output directory for LoRA adapters",
    )
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--lr", type=float, default=DEFAULT_LR)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--grad-accum", type=int, default=DEFAULT_GRAD_ACCUM)
    parser.add_argument("--max-seq-len", type=int, default=DEFAULT_MAX_SEQ_LEN)
    parser.add_argument("--lora-r", type=int, default=DEFAULT_LORA_R)
    parser.add_argument("--lora-alpha", type=int, default=DEFAULT_LORA_ALPHA)
    args = parser.parse_args()

    train_path = Path(args.train_data)
    val_path = Path(args.val_data)

    if not train_path.exists():
        logger.error("train_data_not_found", path=str(train_path))
        logger.info("hint", run="uv run python -m src.pipelines.prepare_finetune_data")
        return

    if not val_path.exists():
        logger.error("val_data_not_found", path=str(val_path))
        return

    train_data = load_jsonl(train_path)
    val_data = load_jsonl(val_path)

    logger.info("data_loaded", train=len(train_data), val=len(val_data))

    model, tokenizer = load_base_model()
    model = apply_lora(model, r=args.lora_r, alpha=args.lora_alpha)

    adapter_path = run_training(
        model=model,
        tokenizer=tokenizer,
        train_data=train_data,
        val_data=val_data,
        output_dir=args.output_dir,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        grad_accum=args.grad_accum,
        max_seq_len=args.max_seq_len,
    )

    logger.info("finetune_pipeline_done", adapter_path=str(adapter_path))


if __name__ == "__main__":
    main()
