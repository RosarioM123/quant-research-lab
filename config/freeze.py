"""Freeze configs before Day 1: ``python -m config.freeze``."""
from .loader import freeze_configs, MANIFEST

if __name__ == "__main__":
    manifest = freeze_configs()
    print(f"froze {len(manifest)} configs -> {MANIFEST}")
