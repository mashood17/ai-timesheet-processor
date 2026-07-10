"""
Section 4/5 step 15 — the most data-sensitive part of the whole system.
Writes ONLY the confirmed day-cell values into the mapped day columns for
matched employee rows. Everything else in the workbook — formulas, styles,
other sheets, merged cells, column widths — must come out byte-for-byte
identical to what went in.

Critical implementation detail: openpyxl only preserves formulas/styles
reliably when the workbook is loaded WITHOUT read_only mode and WITHOUT
data_only=True (data_only=True would silently replace formula cells with
their last-calculated value, permanently destroying the formula — never do
that here). We load once, mutate only the specific cells the mapping
identifies, and save back to a NEW file path so the original upload is
never touched.
"""
import shutil
from pathlib import Path

import openpyxl
from openpyxl.utils import column_index_from_string

from app.models.process_models import CorrectedCell, EmployeeProcessResult


class ExcelWriterService:
    def write_confirmed_hours(
        self,
        source_excel_path: Path,
        sheet_name: str,
        output_path: Path,
        results: list[EmployeeProcessResult],
        corrections: list[CorrectedCell],
        day_columns: dict[str, str],  # {iso_date: excel_column_letter}
    ) -> dict:
        """
        Returns a small summary dict: {matched_written, cells_written, manually_corrected}.
        """
        # Never mutate the original upload — copy first, then edit the copy.
        shutil.copyfile(source_excel_path, output_path)

        workbook = openpyxl.load_workbook(output_path, data_only=False)
        sheet = workbook[sheet_name]

        # Index corrections for O(1) lookup: (normalized_iqama, iso_date) -> corrected_value
        correction_index: dict[tuple[str, str], str] = {
            (self._normalize(c.iqama_or_passport), c.iso_date): c.corrected_value
            for c in corrections
        }

        matched_written = 0
        cells_written = 0
        manually_corrected = 0

        for employee in results:
            if not employee.matched or employee.excel_row is None:
                continue  # unmatched rows are never written — Section 5 step 12/15

            normalized_iqama = self._normalize(employee.iqama_or_passport)
            wrote_any_cell_for_this_employee = False

            for day_cell in employee.day_cells:
                excel_col_letter = day_columns.get(day_cell.iso_date)
                if not excel_col_letter:
                    continue  # date wasn't part of the confirmed mapping — skip, don't guess

                correction_key = (normalized_iqama, day_cell.iso_date)
                if correction_key in correction_index:
                    final_value = correction_index[correction_key]
                    manually_corrected += 1
                else:
                    final_value = day_cell.value

                if final_value in (None, "?", ""):
                    continue  # unresolved cell with no correction supplied — leave blank, don't write "?"

                col_idx = column_index_from_string(excel_col_letter)
                target_cell = sheet.cell(row=employee.excel_row, column=col_idx)

                # BUGFIX: some master workbooks reuse a date-formatted style on
                # the day-column data cells (leftover from a date header row
                # above), which silently renders a written number like 10 as a
                # date serial ("1900-01-10") instead of "10 hours". We must
                # explicitly force a plain number/text format on write —
                # never trust whatever format the cell already has here.
                if final_value.isdigit():
                    target_cell.value = int(final_value)
                    target_cell.number_format = "General"
                else:
                    target_cell.value = final_value
                    target_cell.number_format = "General"

                cells_written += 1
                wrote_any_cell_for_this_employee = True

            if wrote_any_cell_for_this_employee:
                matched_written += 1

        workbook.save(output_path)
        workbook.close()

        return {
            "matched_written": matched_written,
            "cells_written": cells_written,
            "manually_corrected": manually_corrected,
        }

    @staticmethod
    def _normalize(value: str | None) -> str:
        if value is None:
            return ""
        return "".join(str(value).split()).upper()