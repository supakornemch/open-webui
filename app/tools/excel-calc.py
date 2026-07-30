"""
title: Excel Calc
author: Haadthip DIO
version: 1.0
required_open_webui_version: 0.5.0

Lets the model compute over an uploaded spreadsheet instead of reading it as text.

Pairs with SKIP_EMBEDDING_EXTENSIONS (app/patches/skip_embedding.py): xlsx/xls/csv
attachments never reach the vector store, so this tool is the only way the model
sees their numbers. Bytes are read straight off Storage and parsed with pandas —
row counts and aggregates stay exact and don't burn context.

Authorization: a file is readable only if it is attached to the current chat
(__files__) or owned by the calling user.
"""

import io
import json
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field

SPREADSHEET_EXTS = ('.xlsx', '.xlsm', '.xls', '.csv')
OPS = ('sum', 'mean', 'median', 'min', 'max', 'count', 'nunique', 'std')
NUMERIC_OPS = ('sum', 'mean', 'median', 'std')


class Tools:
    class Valves(BaseModel):
        max_rows: int = Field(
            default=200,
            description='Hard cap on rows returned by read_sheet in one call',
        )
        max_groups: int = Field(
            default=200,
            description='Hard cap on groups returned by aggregate',
        )

    def __init__(self):
        self.valves = self.Valves()
        self._cache: tuple[str, str, bytes] | None = None

    # ── file access ─────────────────────────────────────────────────────────

    async def _bytes(
        self, file_id: str, files: Optional[list[dict]], user: Optional[dict]
    ) -> tuple[str, bytes]:
        if self._cache and self._cache[0] == file_id:
            return self._cache[1], self._cache[2]

        from open_webui.models.files import Files
        from open_webui.storage.provider import Storage

        file = await Files.get_file_by_id(file_id)
        if not file:
            raise ValueError(f'file not found: {file_id}')

        attached = {
            item.get('id')
            for item in (files or [])
            if isinstance(item, dict) and item.get('type', 'file') == 'file'
        }
        user_id = (user or {}).get('id')
        if file_id not in attached and file.user_id != user_id:
            raise PermissionError(f'no access to file: {file_id}')

        with open(Storage.get_file(file.path), 'rb') as fh:
            blob = fh.read()

        self._cache = (file_id, file.filename, blob)
        return file.filename, blob

    @staticmethod
    def _sheet_names(filename: str, blob: bytes) -> list[str]:
        if filename.lower().endswith('.csv'):
            return ['csv']
        return pd.ExcelFile(io.BytesIO(blob)).sheet_names

    @staticmethod
    def _frame(filename: str, blob: bytes, sheet: Optional[str], header_row: int) -> pd.DataFrame:
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(io.BytesIO(blob), header=header_row)
        else:
            xls = pd.ExcelFile(io.BytesIO(blob))
            name = sheet if sheet in xls.sheet_names else xls.sheet_names[0]
            df = xls.parse(name, header=header_row)
        df.columns = [str(c).strip() for c in df.columns]
        return df

    async def _prepared(
        self,
        file_id: str,
        sheet: Optional[str],
        query: Optional[str],
        header_row: int,
        files: Optional[list[dict]],
        user: Optional[dict],
    ) -> tuple[str, pd.DataFrame]:
        filename, blob = await self._bytes(file_id, files, user)
        df = self._frame(filename, blob, sheet, header_row)
        if query:
            df = df.query(query)
        return filename, df

    # ── tools ───────────────────────────────────────────────────────────────

    async def list_spreadsheets(
        self,
        __files__: Optional[list[dict]] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        List the spreadsheets attached to this chat, with their sheet names, column
        names and row counts. Call this first to learn the file_id and the exact
        column spelling needed by read_sheet and aggregate.

        :return: JSON array of files, each with id, filename and sheets
        """
        out = []
        for item in __files__ or []:
            if not isinstance(item, dict) or item.get('type', 'file') != 'file':
                continue
            file_id = item.get('id')
            name = item.get('name') or item.get('filename') or ''
            if not file_id or not str(name).lower().endswith(SPREADSHEET_EXTS):
                continue
            try:
                filename, blob = await self._bytes(file_id, __files__, __user__)
                sheets = []
                for sn in self._sheet_names(filename, blob):
                    df = self._frame(filename, blob, sn, 0)
                    sheets.append(
                        {'sheet': sn, 'rows': int(len(df)), 'columns': list(df.columns)}
                    )
                out.append({'id': file_id, 'filename': filename, 'sheets': sheets})
            except Exception as e:
                out.append({'id': file_id, 'filename': str(name), 'error': str(e)})

        if not out:
            return json.dumps(
                {'files': [], 'hint': 'No spreadsheet attached. Ask the user to upload .xlsx or .csv.'},
                ensure_ascii=False,
            )
        return json.dumps({'files': out}, ensure_ascii=False)

    async def read_sheet(
        self,
        file_id: str,
        sheet: Optional[str] = None,
        columns: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        header_row: int = 0,
        __files__: Optional[list[dict]] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Read rows from a spreadsheet as records. Use it to inspect data, not to pull
        the whole file — filter with query and narrow with columns instead.

        :param file_id: File id from list_spreadsheets
        :param sheet: Sheet name. Defaults to the first sheet
        :param columns: Comma-separated column names to return. Defaults to all
        :param query: pandas query expression, e.g. Qty > 100 and Region == "North". Wrap column names containing spaces in backticks
        :param limit: Rows to return (capped by the max_rows valve)
        :param offset: Rows to skip, for paging
        :param header_row: 0-indexed row holding the column headers
        :return: JSON with total matched rows and the selected records
        """
        try:
            filename, df = await self._prepared(
                file_id, sheet, query, header_row, __files__, __user__
            )
        except Exception as e:
            return json.dumps({'error': str(e)}, ensure_ascii=False)

        if columns:
            wanted = [c.strip() for c in columns.split(',') if c.strip()]
            missing = [c for c in wanted if c not in df.columns]
            if missing:
                return json.dumps(
                    {'error': f'unknown columns: {missing}', 'available': list(df.columns)},
                    ensure_ascii=False,
                )
            df = df[wanted]

        total = int(len(df))
        limit = max(1, min(int(limit), self.valves.max_rows))
        offset = max(0, int(offset))
        page = df.iloc[offset : offset + limit]

        return json.dumps(
            {
                'filename': filename,
                'total_rows': total,
                'offset': offset,
                'returned': int(len(page)),
                'records': json.loads(page.to_json(orient='records', date_format='iso')),
            },
            ensure_ascii=False,
        )

    async def aggregate(
        self,
        file_id: str,
        op: str,
        column: Optional[str] = None,
        sheet: Optional[str] = None,
        group_by: Optional[str] = None,
        query: Optional[str] = None,
        header_row: int = 0,
        __files__: Optional[list[dict]] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Compute an aggregate over a spreadsheet column, optionally grouped. Prefer this
        over reading rows and adding them up yourself — the result is exact and covers
        every matching row, not just the ones returned.

        :param file_id: File id from list_spreadsheets
        :param op: One of sum, mean, median, min, max, count, nunique, std
        :param column: Column to aggregate. Omit only when op is count
        :param sheet: Sheet name. Defaults to the first sheet
        :param group_by: Comma-separated columns to group by
        :param query: pandas query expression applied before aggregating
        :param header_row: 0-indexed row holding the column headers
        :return: JSON with the aggregate result, or one row per group
        """
        op = str(op).strip().lower()
        if op not in OPS:
            return json.dumps({'error': f'op must be one of {list(OPS)}'}, ensure_ascii=False)

        try:
            filename, df = await self._prepared(
                file_id, sheet, query, header_row, __files__, __user__
            )
        except Exception as e:
            return json.dumps({'error': str(e)}, ensure_ascii=False)

        if column and column not in df.columns:
            return json.dumps(
                {'error': f'unknown column: {column}', 'available': list(df.columns)},
                ensure_ascii=False,
            )

        if op in NUMERIC_OPS and column and not pd.api.types.is_numeric_dtype(df[column]):
            # sum on a text column would concatenate and hand the model a bogus total
            return json.dumps(
                {
                    'error': f'column {column!r} is not numeric, so {op} is meaningless',
                    'hint': 'pick a numeric column, or use count/nunique/min/max',
                },
                ensure_ascii=False,
            )

        groups = [c.strip() for c in (group_by or '').split(',') if c.strip()]
        missing = [c for c in groups if c not in df.columns]
        if missing:
            return json.dumps(
                {'error': f'unknown group_by columns: {missing}', 'available': list(df.columns)},
                ensure_ascii=False,
            )

        base = {'filename': filename, 'op': op, 'column': column, 'matched_rows': int(len(df))}

        try:
            if not groups:
                value = len(df) if op == 'count' and not column else getattr(df[column], op)()
                base['result'] = None if pd.isna(value) else value.item() if hasattr(value, 'item') else value
                return json.dumps(base, ensure_ascii=False, default=str)

            target = df.groupby(groups, dropna=False)
            series = target.size() if op == 'count' and not column else getattr(target[column], op)()
            result = series.reset_index(name='value' if series.name is None else series.name)
            result = result.rename(columns={column: 'value'}) if column in result.columns else result
        except Exception as e:
            return json.dumps({**base, 'error': str(e)}, ensure_ascii=False)

        base['groups'] = int(len(result))
        base['truncated'] = len(result) > self.valves.max_groups
        base['results'] = json.loads(
            result.head(self.valves.max_groups).to_json(orient='records', date_format='iso')
        )
        return json.dumps(base, ensure_ascii=False, default=str)
