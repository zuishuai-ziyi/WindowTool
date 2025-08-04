import os, yaml
from typing import Any

DEFAULT_CONFIG = {
    "set_up": {
        "keep_work_time": -1.0,
        "on_top_time": -1.0,
        "allow_minimize": True
    }
}

class Profile:
    def __init__(self, profile_path, /) -> None:
        # 验证并设置属性
        self.profile_path = profile_path
        if not os.path.exists(profile_path):
            print(f"[INFO]  文件 {profile_path} 不存在，正在创建")
            self.create()

    def __enter__(self):
        # 进入 with 块时，返回自身
        return self

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
        return True
    
    def write(self, d: dict) -> None:
        '''向配置文件中写入字典'''
        print('[TRACE] 保存配置文件')
        with open(self.profile_path, 'w+', encoding='utf-8') as f:
            yaml.dump(d, f)
        return None


class ProfileShell:
    def __init__(self, profile_path: str) -> None:
        self.profile_path_obj = Profile(profile_path)
        self.default_data: dict[str, Any] = {}
    
    def register(self, key: str, default_value: Any):
        '''注册键的默认值'''
        self.default_data[key] = default_value
    
    def unregister(self, key: str):
        '''取消注册键的默认值'''
        del self.default_data[key]

    def __getitem__(self, key) -> Any:
        default = object()
        data: object | dict = t if isinstance(t := self.profile_path_obj.get(), dict) else default
        if data == default:
            # 不存在目标键或数据类型错误，返回注册的默认值
            return self.default_data[key] if key in self.default_data else None
        dict_data: Any = data.get(key, default)  # type: ignore # 获取数据
        # 存在目标键，返回目标键对应值
        return dict_data
    
    def get(self, key, default = None) -> Any:
        defa_obj = object()
        data: object | dict = t if isinstance(t := self.profile_path_obj.get(), dict) else defa_obj
        if data == defa_obj:
            return default
        return  data.get(key, default) # type: ignore

    def __setitem__(self, key: str, value: Any) -> None:
        try:
            self.profile_path_obj.set(key, value)
        except Exception as e:
            print(f'[Error] 写入配置文件时出现错误：{e}')
            raise
        return None

    def __delitem__(self, key: str) -> None:
        default = object()
        data: object | dict = t if isinstance(t := self.profile_path_obj.get(), dict) else default
        if data == default:
            # 不存在目标键或数据类型错误，返回注册的默认值
            print(f'[Warnning] 删除的目标键 {key} 不存在')
            return None
        new_profile_data: dict = data.get() # type: ignore
        del new_profile_data[key]
        self.profile_path_obj.write(new_profile_data)
        return None


if __name__ == '__main__':
    obj = ProfileShell('.\\test.yaml')
    print(obj['a'])
    obj['a'] = 5
    print(obj['a'])
    # del obj['a']
    # print(obj['a'])
