from pathlib import Path
import pandas as pd


def append_knowledge_records(records: pd.DataFrame, knowledge_dir: Path | str) -> Path:
    knowledge_path = Path(knowledge_dir)
    knowledge_path.mkdir(parents=True, exist_ok=True)
    file_path = knowledge_path / "knowledge_base.csv"
    if file_path.exists():
        existing = pd.read_csv(file_path, parse_dates=["date"])
        merged = pd.concat([existing, records], ignore_index=True)
    else:
        merged = records.copy()
    merged.to_csv(file_path, index=False)
    return file_path
