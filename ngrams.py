import io
import os
import pathlib
import sys

from collections import Counter

from typing import Tuple

from util import collect_ngrams, export_ngrams, handle_broken_pipe_error, iter_files

INPUT_ENCODING = "utf-8"
MAX_SAMPLE_LENGTH = 256
OUTPUT_ENCODING = "utf-8"
PROGRESS_INTERVAL = 1000


@handle_broken_pipe_error
def main() -> None:
    script_name, *args = sys.argv
    script_base = os.path.basename(script_name)

    if len(args) < 2:
        print(
            f"Usage: {script_base} <path_src> <dpath_src> [<pattern> ...]",
            file=sys.stderr,
        )
        sys.exit(1)

    path_src = pathlib.Path(args[0]).expanduser().resolve()
    dpath_dest = pathlib.Path(args[1]).expanduser().resolve()
    patterns = args[2:]

    if not dpath_dest.is_dir():
        print(f"Error: '{dpath_dest}' is not a valid directory", file=sys.stderr)
        sys.exit(1)

    ngrams: dict[Tuple[int, bool], Counter[str]] = {}
    printed_progress = False
    total_file_count = 0

    for _name, file in iter_files(path_src, patterns):
        total_file_count += 1
        if total_file_count % PROGRESS_INTERVAL == 0:
            print(".", end="", file=sys.stderr, flush=True)
            printed_progress = True
        with io.TextIOWrapper(file, encoding=INPUT_ENCODING) as file:
            collect_ngrams(file, ngrams)

    if printed_progress:
        print(file=sys.stderr, flush=True)

    print(f"files: {total_file_count}")
    print()

    export_ngrams(ngrams, MAX_SAMPLE_LENGTH, dpath_dest, OUTPUT_ENCODING)


if __name__ == "__main__":
    main()
