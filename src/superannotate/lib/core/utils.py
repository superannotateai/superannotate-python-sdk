def chunkify(lst, n):
    """Divide the list `lst` into chunks of size `n`."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]
