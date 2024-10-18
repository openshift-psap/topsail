from typing import List, Optional
import os
import subprocess
import logging

logger = logging.getLogger(__name__)




def get_checkpoint_and_refs_dir(
    model_id: str,
    bucket_uri: str,
    s3_sync_args: Optional[List[str]] = None,
    mkdir: bool = False,
) -> str:


    return model_id, "not used"


def get_download_path(model_id: str):
    return model_id


def download_model(
    model_id: str,
    bucket_uri: str,
    s3_sync_args: Optional[List[str]] = None,
    tokenizer_only: bool = False,
) -> None:
   pass


def get_mirror_link(model_id: str) -> str:
    return "not used"
