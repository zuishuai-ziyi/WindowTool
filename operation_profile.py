import os, yaml
from enum import IntEnum, auto
from typing import Any, Self, Dict, List, Type, NoReturn, Iterable, Callable, TypeVar
from pathlib import Path
DEFAULT_CONFIG = {
    "set_up": {
        "keep_work_time": -1.0,
        "on_top_time": -1.0,
        "allow_minimize": True
    }
}

class profile:
    def __init__(self, profile_path, /) -> None:
        # 验证并设置属性
        self.profile_path = profile_path
        if not os.path.exists(profile_path):
            print(f"[INFO]  文件 {profile_path} 不存在，正在创建")
            self.create()

OperationData = Dict[str, Any]
'''操作的数据'''

    def __exit__(self, *args) -> None:
        return None
    
    def create(self) -> None:
        '''创建配置文件'''
        try:
            os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
            with open(self.profile_path, 'w+', encoding='utf-8') as f:
                yaml.dump(DEFAULT_CONFIG, f)
            print(f"[INFO]  配置文件 {self.profile_path} 创建成功")
        except Exception as e:
            print(f"[ERROR] 配置文件创建失败，错误信息：{e}")
            raise e
    
    def get(self) -> dict[Any, Any]:
        '''获取配置文件内容'''
        if not os.path.exists(self.profile_path):
            raise FileNotFoundError(f"文件 {self.profile_path} 不存在")

        with open(self.profile_path, 'r', encoding='utf-8') as f:
            try:
                data: Any = yaml.safe_load(f)
            except Exception:
                print(f"[ERROR] 配置文件格式错误，重新初始化……")
                self.create()
                return self.get()

        if not isinstance(data, dict):
            print(f"[WARN]  数据类型错误，预期: dict，实际: {type(data)}")
            # 打印调用栈
            import traceback
            traceback.print_stack()
            return {}
        return data
    
    def set(self, key: str, value: Any) -> bool:
        '''更改配置文件置顶键值对的内容；若目标键值对不存在，则创建；若目标配置文件中数据类型不为字典，不做任何更改并返回 False'''
        if not os.path.exists(self.profile_path):
            raise FileNotFoundError(f"文件 {self.profile_path} 不存在")
        
        print('[TRACE] 设置配置文件键值对')
        data = self.get()
        with open(self.profile_path, 'w+', encoding='utf-8') as f:
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
    
    def write(self, d: dict) -> None:
        '''向配置文件中写入字典'''
        print('[TRACE] 保存配置文件')
        with open(self.profile_path, 'w+', encoding='utf-8') as f:
            yaml.dump(d, f)
        return None

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
