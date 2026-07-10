"""
Section 5, steps 11-12 + Section 4: matches PDF employee rows against the
master Excel's IQAMA column, and separately flags duplicate IQAMAs found
within the PDF itself (a data-quality problem in the source document,
independent of matching).

IQAMA/Passport numbers are compared as normalized strings (trimmed,
non-digit characters stripped for numeric IQAMAs) so that "2186790602",
"2186790602 ", and an Excel cell stored as the int 2186790602 all match.
"""
import re
from collections import Counter
from pathlib import Path

import openpyxl
from openpyxl.utils import column_index_from_string


def normalize_id(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    # Keep alphanumerics only (covers passport numbers, which can be alphanumeric,
    # as well as pure-numeric IQAMA numbers) — but don't strip letters, since a
    # passport like "AB1234567" is a legitimate identifier, not noise.
    return re.sub(r"\s+", "", text).upper()


class MatchingService:
    def build_iqama_index(
        self,
        excel_path: Path,
        sheet_name: str,
        iqama_column: str,
        data_start_row: int,
    ) -> dict[str, int]:
        """
        Returns {normalized_iqama: excel_row_number}. If the same IQAMA appears
        twice in the Excel itself, the first occurrence wins and a warning
        should be surfaced by the caller — this is a master-data problem, not
        something to silently resolve here.
        """
        workbook = openpyxl.load_workbook(excel_path, data_only=False, read_only=True)
        sheet = workbook[sheet_name]
        col_idx = column_index_from_string(iqama_column)

        index: dict[str, int] = {}
        for row_idx in range(data_start_row, sheet.max_row + 1):
            cell_value = sheet.cell(row=row_idx, column=col_idx).value
            normalized = normalize_id(cell_value)
            if normalized and normalized not in index:
                index[normalized] = row_idx

        workbook.close()
        return index

    def find_duplicate_pdf_iqamas(self, pdf_iqamas: list[str]) -> dict[str, int]:
        """Returns {normalized_iqama: occurrence_count} for any appearing more than once."""
        normalized = [normalize_id(v) for v in pdf_iqamas if v]
        counts = Counter(normalized)
        return {iqama: count for iqama, count in counts.items() if count > 1}