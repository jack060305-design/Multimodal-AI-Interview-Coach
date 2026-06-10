"""Print accelerator profile — run: python scripts/check_gpu.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.device import accelerator_status_dict, log_accelerator_profile

if __name__ == "__main__":
    log_accelerator_profile()
    profile = accelerator_status_dict()
    print("\nAccelerator profile:")
    for key, value in profile.items():
        print(f"  {key}: {value}")
