"""Ingest sample rubrics into Chroma vector store."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rubric_engine.store_factory import get_vector_store
from rubrics.sample_rubrics import SAMPLE_RUBRICS


def main() -> None:
    store = get_vector_store()
    count = store.ingest(SAMPLE_RUBRICS)
    target = getattr(store, "persist_dir", "pinecone")
    print(f"Ingested {count} rubrics into {target}")


if __name__ == "__main__":
    main()
