from io import BytesIO

import pandas as pd

from backend.models import CategoryScore, ScoreResponse


def _category_dataframe(category: CategoryScore) -> pd.DataFrame:
    rows = [
        {
            "מדד": ind.label,
            "ערך נמדד": ind.raw_value,
            "סף": ind.threshold,
            "תוצאה": ind.result,
            "סוג": "אוטומטי" if ind.automatic else "ידני",
        }
        for ind in category.indicators
    ]
    rows.append({"מדד": "סה\"כ", "ערך נמדד": "", "סף": "", "תוצאה": category.total, "סוג": ""})
    return pd.DataFrame(rows)


def build_excel(response: ScoreResponse) -> BytesIO:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        _category_dataframe(response.environment).to_excel(writer, sheet_name="ציון סביבה", index=False)
        _category_dataframe(response.design).to_excel(writer, sheet_name="ציון תכנון", index=False)

        summary = pd.DataFrame(
            [
                {"קטגוריה": "ציון סביבה", "סה\"כ": response.environment.total},
                {"קטגוריה": "ציון תכנון", "סה\"כ": response.design.total},
            ]
        )
        summary.to_excel(writer, sheet_name="סיכום", index=False)

    buffer.seek(0)
    return buffer
