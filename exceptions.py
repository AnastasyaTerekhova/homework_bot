class NoKeyException(Exception):
    """Исключение при отсутствии нужного ключа."""

    pass


class UnknownStatusException(Exception):
    """Исключение при неизвесном статусе домашки."""

    pass


class UnexpectedStatusException(Exception):
    """Статус ответа не равен 200."""

    pass
