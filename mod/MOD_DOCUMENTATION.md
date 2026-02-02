# Mod系统文档

## 概述

Mod系统是WindowTool的扩展机制，允许用户通过添加mod来增强WindowTool的功能。Mod可以添加新的窗口操作、扩展UI、实现自定义功能等。

## 目录结构

```
mod/
├── mod_interface.py     # mod接口定义
├── mod_manager.py       # mod管理器
├── mods/                # mod存放目录
│   └── example_mod/     # 示例mod
└── MOD_DOCUMENTATION.md # mod系统文档
```

## 创建Mod

### 方式一：单文件Mod

创建一个 `.py` 文件，放在 `mod/mods/` 目录下。

### 方式二：目录Mod

创建一个目录，放在 `mod/mods/` 目录下，目录中必须包含 `__init__.py` 文件。

## Mod结构

一个完整的mod需要包含以下内容：

1. **Mod信息**：定义mod的ID、名称和版本
2. **Mod类**：继承自 `ModInterface` 并实现所有抽象方法
3. **生命周期方法**：`on_load`、`on_start`、`on_stop`、`on_unload`
4. **消息处理方法**：`handle_message`

## 示例Mod

### 单文件Mod示例

```python
"""
测试mod
"""
from mod.mod_interface import ModInterface
import logging

# mod信息
MOD_ID = "test_mod"
MOD_NAME = "测试Mod"
MOD_VERSION = "1.0.0"

class TestMod(ModInterface):
    """测试mod类"""
    
    def __init__(self, mod_id, mod_name, mod_version):
        super().__init__(mod_id, mod_name, mod_version)
        self.logger.info("TestMod初始化成功")
    
    def on_load(self, host_api):
        """mod加载时调用"""
        self.host_api = host_api
        self.logger.info("TestMod加载成功")
        return True
    
    def on_start(self):
        """mod启动时调用"""
        self.logger.info("TestMod启动成功")
        # 发送测试消息
        test_message = {
            "message_type": "event",
            "topic": "test",
            "action": "test_event",
            "data": {"message": "TestMod启动了！"},
            "sender": self.mod_id,
            "recipient": None
        }
        self.host_api.send_message_to_all_mods(test_message)
        return True
    
    def on_stop(self):
        """mod停止时调用"""
        self.logger.info("TestMod停止成功")
        return True
    
    def on_unload(self):
        """mod卸载时调用"""
        self.logger.info("TestMod卸载成功")
        return True
    
    def handle_message(self, message):
        """处理来自主程序或其他mod的消息"""
        self.logger.info(f"TestMod收到消息: {message}")
        
        # 回复消息
        if message.get("recipient") == self.mod_id:
            return {
                "message_type": "response",
                "topic": message.get("topic", "core"),
                "action": message.get("action", ""),
                "data": {"response": "TestMod已收到消息"},
                "sender": self.mod_id,
                "recipient": message.get("sender"),
                "message_id": message.get("message_id")
            }
        
        return None
```

### 目录Mod示例

```
mods/
example_mod/
├── __init__.py
├── main.py
└── utils.py
```

**__init__.py**

```python
"""
示例mod
"""
from .main import ExampleMod

# mod信息
MOD_ID = "example_mod"
MOD_NAME = "示例Mod"
MOD_VERSION = "1.0.0"

# 导出mod类
__all__ = ["ExampleMod"]
```

**main.py**

```python
"""
示例mod主文件
"""
from mod.mod_interface import ModInterface
from .utils import do_something

class ExampleMod(ModInterface):
    """示例mod类"""
    
    def __init__(self, mod_id, mod_name, mod_version):
        super().__init__(mod_id, mod_name, mod_version)
        self.logger.info("ExampleMod初始化成功")
    
    def on_load(self, host_api):
        """mod加载时调用"""
        self.host_api = host_api
        self.logger.info("ExampleMod加载成功")
        return True
    
    def on_start(self):
        """mod启动时调用"""
        self.logger.info("ExampleMod启动成功")
        do_something()
        return True
    
    def on_stop(self):
        """mod停止时调用"""
        self.logger.info("ExampleMod停止成功")
        return True
    
    def on_unload(self):
        """mod卸载时调用"""
        self.logger.info("ExampleMod卸载成功")
        return True
    
    def handle_message(self, message):
        """处理来自主程序或其他mod的消息"""
        self.logger.info(f"ExampleMod收到消息: {message}")
        return None
```

**utils.py**

```python
"""
示例mod工具函数
"""
def do_something():
    """做一些事情"""
    print("ExampleMod: 做一些事情")
```

## Mod管理

### 通过UI管理Mod

1. 打开WindowTool主窗口
2. 点击 "Mod管理" 按钮
3. 在Mod管理窗口中，可以：
   - 查看所有mod的状态
   - 加载/卸载mod
   - 启动/停止mod
   - 移除mod
   - 打开mods文件夹

### 命令行管理

目前不支持命令行管理mod，所有操作都通过UI进行。

## Mod通信

Mod之间可以通过消息系统进行通信。消息格式遵循 `ModCommunicationProtocol` 定义的标准格式。

### 发送消息

```python
# 发送消息到指定mod
response = self.host_api.send_message_to_mod("target_mod_id", message)

# 发送消息到所有mod
responses = self.host_api.send_message_to_all_mods(message)
```

### 消息格式

```python
{
    "message_type": "request",  # 消息类型：request, response, event
    "topic": "core",           # 消息主题：core, ui, window, process, mod
    "action": "get_info",      # 消息动作
    "data": {},                # 消息数据
    "sender": "mod_id",        # 发送者
    "recipient": "target_id",  # 接收者，None表示广播
    "message_id": "uuid",       # 消息ID
    "timestamp": 1234567890     # 时间戳
}
```

## 访问WindowTool功能

Mod可以通过 `host_api` 访问WindowTool的核心功能：

```python
# 获取WindowTool核心功能
window_tool_functions = self.host_api.get_window_tool_functions()

# 使用核心功能
if window_tool_functions.get("get_top_window_under_mouse"):
    pid, hwnd = window_tool_functions["get_top_window_under_mouse"]()
    print(f"当前鼠标下的窗口: PID={pid}, HWND={hwnd}")
```

## 最佳实践

1. **命名规范**：
   - Mod ID 应该唯一且使用小写字母和下划线
   - Mod名称应该简洁明了
   - 版本号应该遵循语义化版本规范

2. **错误处理**：
   - 在mod的各个方法中添加适当的错误处理
   - 使用 `self.logger` 记录日志，而不是直接打印

3. **资源管理**：
   - 在 `on_unload` 方法中释放所有资源
   - 避免内存泄漏

4. **性能考虑**：
   - 避免在 `handle_message` 中执行耗时操作
   - 对于长时间运行的任务，考虑使用线程

## 故障排除

### Mod加载失败

- 检查mod文件是否存在
- 检查mod是否正确实现了 `ModInterface` 接口
- 检查mod的依赖是否满足
- 查看日志文件中的错误信息

### Mod启动失败

- 检查 `on_start` 方法是否正确实现
- 检查mod是否有未处理的异常
- 查看日志文件中的错误信息

### 消息通信失败

- 检查消息格式是否正确
- 检查接收mod是否已加载和启动
- 查看日志文件中的错误信息

## 示例Mod功能

### 1. 窗口操作扩展

创建一个mod，添加新的窗口操作，如窗口透明度调整、窗口置顶等。

### 2. UI扩展

创建一个mod，添加新的UI元素，如自定义面板、工具栏等。

### 3. 系统集成

创建一个mod，与其他系统或服务集成，如与系统剪贴板、文件系统等交互。

### 4. 自动化任务

创建一个mod，实现自动化任务，如定时窗口操作、批量窗口管理等。

## 总结

Mod系统为WindowTool提供了强大的扩展能力，允许用户根据自己的需求定制和增强WindowTool的功能。通过遵循本文档的指导，您可以创建各种类型的mod来扩展WindowTool的能力。
