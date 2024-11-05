import torch
import torch.distributed

from torch.nn.parallel import DistributedDataParallel as DDP
from datasets import load_dataset
from peft import get_peft_model, LoraConfig
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)


TASK_TYPE = "CAUSAL_LLM"
MODEL_NAME_OR_PATH = "/mnt/storage/model/granite-3b-code-instruct"
TOKENIZER_NAME_OR_PATH = None
DATASET_PATH = "/mnt/output/dataset.json"
CACHE_DIR = "./cache_dir"
OUTPUT_DIR = "/mnt/output/fine-tuning"
MAX_SEQ_LENGTH = 1024


def train_func():
    # https://www.kubeflow.org/docs/components/training/getting-started/
    # setup Pytorch DDP. WORLD_SIZE and RANK environments will be set by Training Operator
    torch.distributed.init_process_group(backend="nccl")
    world_size = torch.distributed.get_world_size()
    rank = torch.distributed.get_rank()

    # setup the device
    device = torch.device(
        f"cuda:{rank}" if torch.cuda.is_available() else "cpu"
    )  # or hardcode it to cuda
    torch.cuda.set_device(device)

    # define peft config (XXX: hardcoded for now)
    peft_config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.1,
        bias="none",
        target_modules=["q_proj", "k_proj"],
        task_type=TASK_TYPE,
    )

    # load pre-trained model
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME_OR_PATH,
        cache_dir=CACHE_DIR,
        attn_implementation="flash_attention_2",  # XXX: make this conditional
    )

    # wrap the model with LoRA: https://huggingface.co/docs/peft/main/conceptual_guides/lora
    model = get_peft_model(model, peft_config)
    # model.print_trainable_parameters()

    model = model.to(device)
    model = DDP(model, device_ids=[rank])

    # load dataset and tokenizer
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
    tokenizer = AutoTokenizer.from_pretrained(
        (TOKENIZER_NAME_OR_PATH if TOKENIZER_NAME_OR_PATH else MODEL_NAME_OR_PATH),
        cache_dir=CACHE_DIR,
        use_fast=True,
        torch_dtype=torch.float16,
    )

    if tokenizer.pad_token is None:
        tokenizer.add_special_tokens({"pad_token": "<PAD>"})

    def preprocess_func(samples):
        result = tokenizer(
            samples["output"],
            truncation=True,
            padding="max_length",
            max_length=MAX_SEQ_LENGTH,
            return_tensors="pt",
        )

        for key, value in result.items():
            result[key] = value.tolist()

        return result

    tokenized_dataset = dataset.map(
        preprocess_func, batched=True, remove_columns=dataset.column_names
    )

    # to handle dynamic padding during training
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    # define training arguments
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        learning_rate=1e-3,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        num_train_epochs=2,
        weight_decay=0.01,
        save_strategy="epoch",
        remove_unused_columns=False,  # to solve error: No columns in the dataset match the model's forward method signature. The following columns have been ignored: [input_ids, attention_mask, output].
        fp16=True,
    )

    # init trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )

    trainer.train()

    # cleanup
    torch.distributed.destroy_process_group()

    if rank == 0:
        print("LoRA fine tuning completed")
        trainer.save_model("lora_model")


train_func()
