"""Check the finite base of the all-order Padé ranking proof."""
from math import factorial


def score(n, m, real, imaginary):
    """Rational form of L/n using exact integers."""
    factorial_scale = factorial(2*m+1)
    remainder_scale = (2*n)**(2*m+1)*factorial(m)
    return (
        2*abs(imaginary)*factorial_scale - remainder_scale,
        2*(abs(real)+abs(imaginary))*factorial_scale,
    )


def verify_small_positive():
    count = 0
    for n in range(2, 256):
        m = 2*n
        coefficients = [factorial(2*m)//factorial(m)]
        for k in range(m):
            next_coefficient, remainder = divmod(
                coefficients[-1]*(m-k), (k+1)*(2*m-k)
            )
            assert remainder == 0
            coefficients.append(next_coefficient)
        real, imaginary = 0, 0
        for coefficient in reversed(coefficients):
            real, imaginary = coefficient - 2*n*imaginary, 2*n*real
        numerator, denominator = score(n, m, real, imaginary)
        assert 1000*n*numerator > denominator, n
        count += 1
    assert count == 254
    print(f"PASS: {count} Horner checks, L(n,2n)>1/1000.")


def main():
    count = 0
    for n in range(2, 7):
        previous, current = (1, 0), (2, 2*n)
        values = [previous, current]
        for m in range(1, 14):
            next_value = tuple(
                2*(2*m+1)*coefficient - (2*n)**2*older
                for older, coefficient in zip(previous, current)
            )
            values.append(next_value)
            previous, current = current, next_value

        for m in range(2*n, 14):
            left_num, left_den = score(n, m, *values[m])
            right_num, right_den = score(n, m+1, *values[m+1])
            assert left_num*right_den < right_num*left_den, (n, m)
            count += 1
    assert count == 30
    print(f"PASS: {count} exact adjacent Padé comparisons.")


if __name__ == "__main__":
    main()
    verify_small_positive()
