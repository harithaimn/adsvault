""" 
Main Runner Script for ingesting ads data from multiple ad accounts with checkpointing.
4 ads accounts to ingest, each may take ~30 mins. This script allows you to run it multiple times without redoing completed accounts.

Run file with:
python -m test._00_1_main_runner_ingest

- since we're storing in test/ folder, not at the package root. so need to run as module.

"""

# python import path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import json
from tqdm import tqdm
#from pathlib import Path

from core._00_1_ad_acc_fetch_pageid import main as ingest_ads

# =========================
# CONFIG
# =========================
AD_ACCOUNTS = [
    "act_379859374796069",  # Decoris | CLIENTS #3 | Malaysia [IOC]
    "act_362641672482631",  # decoris | INTERNAL | Malaysia | [IOC]
    #"act_1836231779759395", # Decoris | CLIENTS#2 | Malaysia | [IOC]
    #"act_775995296641112",  # Decoris | CLIENTS#1 | Malaysia | [IOC]
]

CHECKPOINT_FILE = "core/_00_0_checkpoint.json"


# =========================
# CHECKPOINT UTILS
# =========================
def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            return json.load(f)
    return {}


def save_checkpoint(state):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(state, f, indent=2)


# =========================
# INGESTION FUNCTION
# =========================
def run_ingestion_for_account(account_id):
    tqdm.write(f"[RUNNING] {account_id}")

    output_path = ingest_ads(account_id)

    tqdm.write(f"[SAVED] {output_path}")
    return True


# =========================
# MAIN RUNNER
# =========================
def main():
    checkpoint = load_checkpoint()

    for acc_id in tqdm(AD_ACCOUNTS, desc="Ad Accounts", unit="acct"):
        status = checkpoint.get(acc_id)

        if status == "done":
            tqdm.write(f"[SKIP] {acc_id} already done")
            continue

        try:
            run_ingestion_for_account(acc_id)

            checkpoint[acc_id] = "done"
            save_checkpoint(checkpoint)

            tqdm.write(f"[DONE] {acc_id}")

        except Exception as e:
            checkpoint[acc_id] = f"error: {str(e)}"
            save_checkpoint(checkpoint)

            tqdm.write(f"[ERROR] {acc_id} → {str(e)}")
            break  # stop here, resume on next run


if __name__ == "__main__":
    main()