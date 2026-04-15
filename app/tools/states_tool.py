from __future__ import annotations

import pandas as pd


class StatsTool:
    name = "stats_tool"
    description = "Provide simple dataframe statistics"

    def run(self, df: pd.DataFrame) -> dict:
        numeric_summary = {}
        try:
            numeric_summary = df.describe(include="number").fillna("").astype(str).to_dict()
        except Exception:
            numeric_summary = {}

        return {
            "shape": list(df.shape),
            "columns": df.columns.tolist(),
            "dtypes": {k: str(v) for k, v in df.dtypes.to_dict().items()},
            "missing_ratio": (df.isna().mean().round(4)).to_dict(),
            "head": df.head(5).fillna("").astype(str).to_dict(orient="records"),
            "numeric_summary": numeric_summary,
        }