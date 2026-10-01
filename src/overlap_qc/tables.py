"""Tabular I/O that dispatches on file extension.

overlap-qc consumes the binary matrix that compact2binary produces, and that
tool can now emit Parquet as well as CSV. This wrapper keeps the two in step:
the reader and writer are chosen from the file extension, so the pipeline reads
and writes CSV, TSV, or Parquet without any call site caring which.

* ``.csv`` / ``.tsv`` - text; read as strings by default so 0/1 indicators and
  ids keep their exact written form.
* ``.parquet`` / ``.pq`` - columnar; requires ``pyarrow`` (``pip install
  '.[parquet]'``). Native dtypes are preserved.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_PARQUET_SUFFIXES = {".parquet", ".pq"}


def _is_parquet(path: str | Path) -> bool:
    return Path(path).suffix.lower() in _PARQUET_SUFFIXES


def read_table(path: str | Path, *, as_str: bool = False) -> pd.DataFrame:
    """Read a table, choosing the reader from the file extension.

    Args:
        path: Input file (.csv, .tsv, .parquet, .pq).
        as_str: For text formats, read every column as string (recommended for
            a raw binary matrix). Ignored for Parquet, which carries its types.
    """
    if _is_parquet(path):
        try:
            return pd.read_parquet(path)
        except ImportError as exc:  # pragma: no cover - depends on env
            raise ImportError(
                "reading Parquet needs pyarrow: pip install '.[parquet]'"
            ) from exc
    sep = "\t" if Path(path).suffix.lower() == ".tsv" else ","
    if as_str:
        return pd.read_csv(path, dtype=str, sep=sep, keep_default_na=True)
    return pd.read_csv(path, sep=sep)


def write_table(df: pd.DataFrame, path: str | Path) -> None:
    """Write a table, choosing the writer from the file extension."""
    if _is_parquet(path):
        try:
            df.to_parquet(path, index=False)
        except ImportError as exc:  # pragma: no cover - depends on env
            raise ImportError(
                "writing Parquet needs pyarrow: pip install '.[parquet]'"
            ) from exc
        return
    sep = "\t" if Path(path).suffix.lower() == ".tsv" else ","
    df.to_csv(path, index=False, sep=sep)
