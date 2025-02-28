
def halton_sequence(n: int, base: int = 2) -> float:
    """Generator function for Halton sequence."""
    l, u = 0, 1
    for _ in range(n):
        x = u - l
        if x == 1:
            l = 1
            u *= base
        else:
            y = u // base
            while x <= y:
                y //= base
            l = (base + 1) * y - x
        yield l / u
