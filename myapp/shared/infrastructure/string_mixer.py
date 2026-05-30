"""String mixer/unmixer used to obfuscate visitor-access ids in URLs."""

from abc import ABC, abstractmethod


class IStringMixer(ABC):
    @abstractmethod
    def mix(self, value: str) -> str: ...

    @abstractmethod
    def unmix(self, mixed: str) -> str: ...


class SecretStringMixer(IStringMixer):
    def __init__(self, secret: str):
        self._secret = secret

    def mix(self, value: str) -> str:
        insert_position = len(self._secret) // 3
        insert_position = min(insert_position, len(self._secret))
        return self._secret[:insert_position] + value + self._secret[insert_position:]

    def unmix(self, mixed: str) -> str:
        insert_position = len(self._secret) // 3
        insert_position = min(insert_position, len(mixed))
        string_length = len(mixed) - len(self._secret)
        return mixed[insert_position : insert_position + string_length]
