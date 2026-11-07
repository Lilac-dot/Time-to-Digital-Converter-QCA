def preclear(flush=16):
    """REF pulse with EN on clears the code, then REF stays low until the line has flushed."""
    return [(0, 0)] * 14 + [(0, 1)] * 6 + [(1, 1)] * 4 + [(0, 1)] * flush
