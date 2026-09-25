from typing import List

import uvicorn


def average(numbers: List[float]) -> float:
    """Возвращает среднее значение списка чисел.

    :param numbers: список чисел
    :return: среднее арифметическое
    :raises ValueError: если список пуст
    """
    if not numbers:
        raise ValueError("Список чисел не может быть пустым")
    return sum(numbers) / len(numbers)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
