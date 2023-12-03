import json

class Config:
    def __init__(self, _path: str) -> None:
        self._path = _path
        self.data = None
        self.load()
    
    def load(self) -> None:
        self.data = json.load(
            open(self._path, encoding="utf-8")
        )