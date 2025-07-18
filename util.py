import functools
import os
import re
import sys
import tarfile
import zipfile

from collections import Counter

from pathlib import Path

from typing import BinaryIO, Callable, Iterable, Iterator, Optional, TextIO, Tuple, TypeVar, Union

F = TypeVar("F", bound=Callable[..., object])


def collect_ngrams(file: Iterable[str], ngrams: dict[Tuple[int, bool], Counter[str]]) -> None:
    for key in [(1, False), (1, True), (2, False), (2, True), (3, False), (3, True)]:
        ngrams.setdefault(key, Counter())
    prev1 = prev1_uc = prev2 = prev2_uc = None
    for line in file:
        for ch in line:
            ch_uc = ch.upper() if "a" <= ch <= "z" else ch
            ngrams[(1, False)][ch] += 1
            ngrams[(1, True)][ch_uc] += 1
            if prev1 is not None:
                ngrams[(2, False)][prev1 + ch] += 1
                ngrams[(2, True)][prev1_uc + ch_uc] += 1
            if prev2 is not None:
                ngrams[(3, False)][prev2 + prev1 + ch] += 1
                ngrams[(3, True)][prev2_uc + prev1_uc + ch_uc] += 1
            prev2, prev1 = prev1, ch
            prev2_uc, prev1_uc = prev1_uc, ch_uc


def escape_char(ch: str) -> str:
    return (
        "\\\\"
        if ch == "\\"
        else f"\\x{ord(ch):02X}" if 0 <= ord(ch) <= 31 or ord(ch) == 127 else ch
    )


def escape_string(s: str) -> str:
    return "".join(escape_char(ch) for ch in s)


def export_ngrams(
    ngrams: dict[Tuple[int, bool], Counter[str]],
    max_sample_length: int,
    dpath_dest: Path,
    encoding: str,
) -> None:
    for n, is_uc in sorted(ngrams.keys()):
        value = ngrams[(n, is_uc)]
        name = f"{n}-grams{'-uc' if is_uc else ''}"
        ngram_to_count_sorted = sorted(value.items(), key=lambda item: item[1], reverse=True)
        print(f"{name} (unique): {len(value)}")
        if n == 1:
            write_sample(value.keys(), max_sample_length)
        print()
        output_path = dpath_dest / f"{name}.tsv"
        with open(output_path, "w", encoding=encoding) as file:
            write_ngram_to_count(file, ngram_to_count_sorted)


def handle_broken_pipe_error(func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        SIGPIPE = 13
        SIGPIPE_EXIT_CODE = 128 + SIGPIPE
        try:
            value = func(*args, **kwargs)
            sys.stdout.flush()
        except BrokenPipeError as e:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            raise SystemExit(SIGPIPE_EXIT_CODE) from e
        return value

    return wrapper


def iter_files(
    path_src: Union[str, Path], patterns: Optional[Iterable[str]] = None
) -> Iterator[Tuple[str, BinaryIO]]:
    compiled_patterns = [re.compile(pattern) for pattern in patterns] if patterns else []

    def matches_patterns(s: str) -> bool:
        if not compiled_patterns:
            return True
        return any(compiled_pattern.search(s) for compiled_pattern in compiled_patterns)

    path_src = Path(path_src)
    if path_src.is_dir():
        for fpath in path_src.rglob("*"):
            if fpath.is_file():
                fpath_relative = fpath.relative_to(path_src).as_posix()
                if matches_patterns(fpath_relative):
                    with fpath.open("rb") as file:
                        yield fpath_relative, file
        return
    if tarfile.is_tarfile(path_src):
        with tarfile.open(path_src, mode="r:*") as file_src:
            for member in file_src.getmembers():
                if not member.isfile():
                    continue
                if not matches_patterns(member.name):
                    continue
                file = file_src.extractfile(member)
                if file is None:
                    continue
                with file:
                    yield member.name, file
        return
    if zipfile.is_zipfile(path_src):
        with zipfile.ZipFile(path_src) as file_src:
            for name in file_src.namelist():
                if name.endswith("/"):
                    continue
                if not matches_patterns(name):
                    continue
                with file_src.open(name) as file:
                    yield name, file
        return
    if path_src.is_file():
        name = path_src.name
        if matches_patterns(name):
            with path_src.open("rb") as file:
                yield name, file
        return
    raise ValueError(
        f"{path_src} is neither a directory, a TAR file, a ZIP file, nor a regular file"
    )


def write_ngram_to_count(file: TextIO, ngram_to_count: Iterable[Tuple[str, int]]) -> None:
    for ngram, count in ngram_to_count:
        print(escape_string(ngram), count, sep="\t", file=file)


def write_sample(keys: Iterable[str], max_length: int) -> None:
    print("".join(escape_string(key) for key in sorted(keys)[:max_length]))
