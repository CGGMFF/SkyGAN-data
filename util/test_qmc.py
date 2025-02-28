from .qmc import halton_sequence

def test_halton():
    assert list(halton_sequence(3)) == [0.5, 0.25, 0.75]
    assert list(halton_sequence(5, base=3)) == [1/3, 2/3, 1/9, 4/9, 7/9]