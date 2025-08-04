import os, yaml
from enum import IntEnum, auto
from typing import Any, Self, Dict, List, Type, NoReturn, Iterable, Callable, TypeVar
from pathlib import Path

class OperationType(IntEnum):
    '''操作类型'''
    SET_ITEM = auto()
    '''设置键值对'''
    SET_ALL = auto()
    '''设置所有键值对'''
    GET = auto()
    '''获取键值对'''
    DEL = auto()
    '''删除键值对'''
    CREATE = auto()
    '''创建配置文件'''

OperationData = Dict[str, Any]
'''操作的数据'''

class Profile:
    def __init__(self, file_path: str) -> None:
        self.file = Path(file_path)
        self.default: Dict = {}
        self.callback: Callable[[OperationType, OperationData], Any] | None = None

    def get[T](self, key:str | None = None, default: None | T = None, *, file_path: None | str = None, using_callback: bool = True) -> T | Dict[str, Any]:
        '''获取配置文件内容'''
        path = self._get_file_path_or_raise_err(file_path)
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        value = data if key is None else data.get(key, default)
        if self.callback and using_callback:
            self.callback(OperationType.GET, {"key": key, "value": value})
        return value

    def set(self, key: str, value: Any, *, file_path: None | str = None, using_callback: bool = True):
        '''更改配置文件置顶键值对的内容'''
        path = self._get_file_path_or_raise_err(file_path)
        data = self.get()
        with open(path, 'w+', encoding='utf-8') as f:
            # print(data)
            data[key] = value
            yaml.dump(data, f)
        if self.callback and using_callback:
            self.callback(OperationType.SET_ITEM, {"key": key, "new_value": value})
        return

    def set_all(self, data, *, file_path: None | str = None, using_callback: bool = True):
        '''设置配置文件内容'''
        path = self._get_file_path_or_raise_err(file_path)
        with open(path, 'w+', encoding='utf-8') as f:
            yaml.dump(data, f)
        if self.callback and using_callback:
            self.callback(OperationType.SET_ALL, {"new_value": data})
        return

    def set_default(self, data: Dict[str, Any]):
        '''设置配置文件默认值'''
        self.default = data
        return

    def check_file(self, data: Dict[str, Type[Any] | Any] | None = None, using_default: bool | None = None) -> bool:
        '''检查配置文件内容是否与给定数据或默认值相同'''
        if not self.file_exists():
            return False
        _data = self.default if data is None else data
        using_default = data is None
        try:
            file_data = self.get()
            return self._check_iterable(file_data, _data, using_default)
        except Exception:
            return False

    def _check_iterable(self, obj1: Iterable, obj2: Iterable, using_default: bool) -> bool:
        # print('check ', obj1, obj2, isinstance(obj1, dict), isinstance(obj2, dict), using_default)
        # 字典
        if isinstance(obj1, dict) and isinstance(obj2, dict):
            return self._check_dict(obj1, obj2, using_default)
        if (not isinstance(obj1, Iterable)) or (not isinstance(obj2, Iterable)):
            return False
        # 其他可迭代对象
        try:
            for elem1, elem2 in zip(obj1, obj2, strict=True):  # strict=True 确保长度相等
                if using_default and ((not isinstance(elem2, Iterable)) or isinstance(elem2, str)):
                    # 使用默认值，获取值的类型
                    elem2 = type(elem2)
                # print('list fot iterable check ', elem1, elem2, using_default, isinstance(elem2, Iterable), isinstance(elem2, str))
                # print('list for ', elem1, elem2)
                if isinstance(elem2, Iterable):
                    # d2包含可迭代对象，检查d1
                    if not isinstance(elem1, Iterable):
                        return False
                    # 递归检查
                    # print(f'递归检查 {elem1}, {elem2}, {type(elem1)}, {type(elem2)}')
                    if not self._check_iterable(elem1, elem2, using_default):
                        return False
                    continue
                # print(elem1, elem2)
                if not isinstance(elem1, elem2):
                    return False
        except ValueError:  # 长度不相等，返回 False
            return False
        return True
    
    def _check_dict(self, d1: Dict[Any, Any], d2: Dict[Any, Any], using_default: bool) -> bool:
        # print('dict check ', d1, d2)
        if d1.keys() != d2.keys():
            return False
        for k in d2:
            v1, v2 = d1[k], d2[k]
            if using_default and ((not isinstance(v2, Iterable)) or isinstance(v2, str)):
                # 使用默认值，获取值的类型
                v2 = type(v2)
            # print('dict for ', v1, v2)
            if isinstance(v2, type):
                # print('check dict for type ', v1, v2)
                # d2包含类型，直接检查类型是否正确
                if not isinstance(v1, v2):
                    return False
            elif isinstance(v2, Iterable):
                # d2包含可迭代对象，递归检查
                if not self._check_iterable(v1, v2, using_default):
                    return False
            else:
                # d2包含无效值
                return False
        return True

    def create(self, data: Dict[str, Any], *, using_callback: bool = True):
        '''创建配置文件'''
        if self.callback and using_callback:
            self.callback(OperationType.CREATE, {"path": self.file, "new_value": data})
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
    
    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.set(key, value)
    
    def __delitem__(self, key):
        data = self.get(key)
        del data[key]
        self.set_all(data)
        return None
    
    def register_callback(self, callback: Callable[[OperationType, OperationData], Any]):
        '''注册回调函数，当操作配置文件时调用'''
        self.callback = callback
        return None
    
    def unregister_callback(self):
        '''注销回调函数'''
        self.callback = None
        return None

if __name__ == '__main__':
    obj = Profile('test.yaml')
    obj.set_default({
        'a': 1,
        'b': 2,
        'c': [
          {
            "name": "test",
            "age": 18
          },
          10,
          '1'
        ]
    })
    res = obj.check_file(
        # {
        #     'a': int,
        #     'b': int,
        #     'c': [
        #         {
        #             'name': str,
        #             'age': int
        #         },
        #         int,
        #         int
        #     ]
        # }
    )
    print(res)
