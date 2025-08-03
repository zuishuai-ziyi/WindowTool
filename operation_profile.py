import os, yaml
from typing import Any, Self, Dict, List, Type, NoReturn
from pathlib import Path

class profile:
    def __init__(self, file_path: str) -> None:
        self.file = Path(file_path)
        self.default = {}

    def get(self, *, file_path: None | str = None) -> Dict[str, Any]:
        '''获取配置文件内容'''
        path = self._get_file_path_or_raise_err(file_path)
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data

    def set(self, key: str, value: Any, *, file_path: None | str = None):
        '''更改配置文件置顶键值对的内容'''
        path = self._get_file_path_or_raise_err(file_path)
        with open(path, 'w+', encoding='utf-8') as f:
            data = self.get()
            data[key] = value
            yaml.dump(data, f)
        return

    def set_all(self, data, *, file_path: None | str = None):
        '''设置配置文件内容'''
        path = self._get_file_path_or_raise_err(file_path)
        with open(path, 'w+', encoding='utf-8') as f:
            yaml.dump(data, f)
        return

    def set_default(self, data):
        '''设置配置文件默认值'''
        self.default = data
        return

    def cheak_file_with_data(self, data: Dict[str, Type[Any]]) -> bool:
        '''检查配置文件内容是否与给定数据相同'''
        if not self.file_exists():
            return False
        file_data = self.get()
        for k, v in data.items():
            if not isinstance(file_data.get(k, object()), v):
                return False
        return True

    def create(self, data: Dict[str, Any]):
        '''创建配置文件'''
        with open(self.file, 'a+', encoding='utf-8') as f:
            yaml.dump(data, f)
        return

    def file_exists(self) -> bool:
        '''检查配置文件是否存在'''
        return self.file.exists()

    def _get_file_path_or_raise_err(self, file: None | str = None) -> str | NoReturn:
        '''检查配置文件/给定文件是否存在并获取，若不存在则抛出异常'''
        path = str(self.file) if file is None else file
        if os.path.exists(path):
            return path
        raise FileNotFoundError(f"文件 {self.file} 不存在")
