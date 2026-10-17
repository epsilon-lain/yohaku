"""Text addresses shared by Yohaku agents and the human JSON/CLI interface.

Positions are 1-based Unicode code-point line/column pairs. Ranges include
their start and exclude their end. LF and CRLF are preserved byte-for-byte;
neither half of CRLF is an addressable character. An empty final line exists
after a trailing newline. These are document coordinates, not screen pixels.
"""
import hashlib

MAX_RANGE_BYTES = 128 * 1024
MAX_TEXT_BYTES = 2 * 1024 * 1024


def lines(text):
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_TEXT_BYTES:
        raise ValueError('Coordinate editing supports UTF-8 text up to 2 MiB')
    result = []
    offset = 0
    # Only LF/CRLF are line separators. Other Unicode separators stay in text.
    chunks = text.split('\n')
    for index, chunk in enumerate(chunks):
        newline = index < len(chunks)-1
        content = chunk[:-1] if newline and chunk.endswith('\r') else chunk
        result.append((offset, content))
        offset += len(chunk) + int(newline)
    return result


def position(table, line, column):
    if type(line) is not int or type(column) is not int or line < 1 or column < 1:
        raise ValueError('Line and column must be positive integers starting at 1')
    if line > len(table) or column > len(table[line-1][1])+1:
        raise ValueError('Text coordinate is outside the document; read the range again')
    return table[line-1][0]+column-1


def bounds(table, start_line, start_column, end_line, end_column):
    start = position(table, start_line, start_column)
    end = position(table, end_line, end_column)
    if end < start:
        raise ValueError('Range end must not precede its start')
    return start, end


def read(text, start_line=1, start_column=1, end_line=None, end_column=None):
    table = lines(text)
    position(table, start_line, start_column)
    if end_line is None:
        end_line = min(start_line+79, len(table))
    if type(end_line) is not int or not 1 <= end_line <= len(table):
        raise ValueError('End line is outside the document')
    if end_column is None:
        # Default pages include their final newline when there is one. The
        # returned end can therefore be the next line's first column.
        if end_line < len(table):
            end_line, end_column = end_line+1, 1
        else:
            end_column = len(table[end_line-1][1])+1
    start, end = bounds(table, start_line, start_column, end_line, end_column)
    selected = text[start:end]
    if len(selected.encode('utf-8')) > MAX_RANGE_BYTES:
        raise ValueError('Requested range exceeds 128 KiB; request fewer lines or columns')
    return {
        'start_line':start_line, 'start_column':start_column,
        'end_line':end_line, 'end_column':end_column, 'text':selected,
        'line_count':len(table), 'eof_line':len(table),
        'eof_column':len(table[-1][1])+1, 'has_more':end < len(text),
        'coordinates':'1-based Unicode characters; start inclusive, end exclusive',
    }


def replace(text, start_line, start_column, end_line, end_column, expected, replacement):
    if not isinstance(expected,str) or not isinstance(replacement,str):
        raise ValueError('Expected text and replacement must be strings')
    table = lines(text)
    start, end = bounds(table, start_line, start_column, end_line, end_column)
    if text[start:end] != expected:
        raise ValueError('Selected text does not match expected; no edit made, read the range again')
    if len(expected.encode('utf-8')) > MAX_RANGE_BYTES or len(replacement.encode('utf-8')) > MAX_RANGE_BYTES:
        raise ValueError('A coordinate replacement must not exceed 128 KiB')
    result = text[:start]+replacement+text[end:]
    lines(result)  # Validate the resulting UTF-8 size before any write.
    return result


def verify(text, expected):
    if text != expected:
        raise ValueError('Read-back does not match the saved edit; inspect current text before retrying')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
