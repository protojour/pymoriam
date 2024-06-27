import os


_1MB = 1000000
_5MB = _1MB * 5
_10MB = _1MB * 10
_100MB = _10MB * 10
_500MB = _1MB * 500
_1000MB = _1MB * 1000


def random_data_gen(size, chunk_size):
    chunk_count = int(size/chunk_size)
    for n in range(chunk_count):
        yield os.urandom(chunk_size)
    if size % chunk_size != 0:
        yield os.urandom(size % chunk_size)
