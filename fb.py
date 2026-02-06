"""FizzBuzz implementation and CLI helper."""
from __future__ import annotations

from typing import List


def fizzbuzz(n: int) -> List[str]:
    """Return the FizzBuzz sequence from 1 to n inclusive."""
    if n < 1:
        return []

    output: List[str] = []
    for value in range(1, n + 1):
        if value % 15 == 0:
            output.append("FizzBuzz")
        elif value % 3 == 0:
            output.append("Fizz")
        elif value % 5 == 0:
            output.append("Buzz")
        else:
            output.append(str(value))
    return output


def main() -> None:
    """Print the FizzBuzz sequence based on user input."""
    raw = input("Ingresa un numero: ").strip()
    if not raw:
        print("Debes ingresar un numero entero positivo.")
        return

    try:
        limit = int(raw)
    except ValueError:
        print("Entrada invalida. Usa un numero entero.")
        return

    for line in fizzbuzz(limit):
        print(line)


if __name__ == "__main__":
    main()
