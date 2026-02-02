"""
mod接口模块，定义mod加载、启动、通信的标准接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
import os

class ModInterface(ABC):
    """mod接口基类，所有mod必须实现此接口"""
    
    def __init__(self, mod_id: str, mod_name: str, mod_version: str):
        """
        初始化mod
        
        Args:
            mod_id: mod唯一标识符
            mod_name: mod名称
            mod_version: mod版本
        """
        self.mod_id = mod_id
        self.mod_name = mod_name
        self.mod_version = mod_version
        self.logger = logging.getLogger(f"mod.{mod_id}")
        self.is_running = False
    
    @abstractmethod
    def on_load(self, host_api: Any) -> bool:
        """
        mod加载时调用
        
        Args:
            host_api: 宿主API，提供mod访问主程序功能的接口
            
        Returns:
            bool: 加载是否成功
        """
        pass
    
    @abstractmethod
    def on_start(self) -> bool:
        """
        mod启动时调用
        
        Returns:
            bool: 启动是否成功
        """
        pass
    
    @abstractmethod
    def on_stop(self) -> bool:
        """
        mod停止时调用
        
        Returns:
            bool: 停止是否成功
        """
        pass
    
    @abstractmethod
    def on_unload(self) -> bool:
        """
        mod卸载时调用
        
        Returns:
            bool: 卸载是否成功
        """
        pass
    
    @abstractmethod
    def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理来自主程序或其他mod的消息
        
        Args:
            message: 消息内容
            
        Returns:
            Optional[Dict[str, Any]]: 回复消息，无回复则返回None
        """
        pass
    
    def get_info(self) -> Dict[str, str]:
        """
        获取mod信息
        
        Returns:
            Dict[str, str]: mod信息
        """
        return {
            "mod_id": self.mod_id,
            "mod_name": self.mod_name,
            "mod_version": self.mod_version,
            "is_running": str(self.is_running)
        }

class ModHostAPI:
    """
    宿主API，提供mod访问主程序功能的接口
    """
    
    def __init__(self, main_app: Any):
        """
        初始化宿主API
        
        Args:
            main_app: 主应用程序实例
        """
        self.main_app = main_app
        self.mod_manager = None
    
    def set_mod_manager(self, mod_manager: Any):
        """
        设置mod管理器
        
        Args:
            mod_manager: mod管理器实例
        """
        self.mod_manager = mod_manager
    
    def send_message_to_mod(self, mod_id: str, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        发送消息到指定mod
        
        Args:
            mod_id: mod唯一标识符
            message: 消息内容
            
        Returns:
            Optional[Dict[str, Any]]: 回复消息，无回复则返回None
        """
        if self.mod_manager:
            return self.mod_manager.send_message(mod_id, message)
        return None
    
    def send_message_to_all_mods(self, message: Dict[str, Any]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        发送消息到所有mod
        
        Args:
            message: 消息内容
            
        Returns:
            Dict[str, Optional[Dict[str, Any]]]: 各mod的回复消息
        """
        if self.mod_manager:
            return self.mod_manager.broadcast_message(message)
        return {}
    
    def get_window_tool_functions(self) -> Dict[str, Any]:
        """
        获取WindowTool的核心功能
        
        Returns:
            Dict[str, Any]: 核心功能字典
        """
        return {
            "get_top_window_under_mouse": self.main_app.get_top_window_under_mouse if hasattr(self.main_app, 'get_top_window_under_mouse') else None,
            "get_window_pos_and_size": self.main_app.get_window_pos_and_size if hasattr(self.main_app, 'get_window_pos_and_size') else None,
            "kill_process": self.main_app.kill_process if hasattr(self.main_app, 'kill_process') else None,
            "suspend_process": self.main_app.suspend_process if hasattr(self.main_app, 'suspend_process') else None,
            "resume_process": self.main_app.resume_process if hasattr(self.main_app, 'resume_process') else None,
        }

class ModCommunicationProtocol:
    """
    mod通信协议
    """
    
    # 消息类型
    MESSAGE_TYPE_REQUEST = "request"
    MESSAGE_TYPE_RESPONSE = "response"
    MESSAGE_TYPE_EVENT = "event"
    
    # 消息主题
    TOPIC_CORE = "core"
    TOPIC_UI = "ui"
    TOPIC_WINDOW = "window"
    TOPIC_PROCESS = "process"
    TOPIC_MOD = "mod"
    
    # 消息动作
    ACTION_GET_INFO = "get_info"
    ACTION_SET_VALUE = "set_value"
    ACTION_EXECUTE = "execute"
    ACTION_SUBSCRIBE = "subscribe"
    ACTION_UNSUBSCRIBE = "unsubscribe"
    
    @staticmethod
    def create_message(
        message_type: str,
        topic: str,
        action: str,
        data: Dict[str, Any],
        sender: str,
        recipient: Optional[str] = None,
        message_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建标准消息
        
        Args:
            message_type: 消息类型
            topic: 消息主题
            action: 消息动作
            data: 消息数据
            sender: 发送者
            recipient: 接收者，None表示广播
            message_id: 消息ID，None则自动生成
            
        Returns:
            Dict[str, Any]: 标准消息格式
        """
        import uuid
        
        return {
            "message_type": message_type,
            "topic": topic,
            "action": action,
            "data": data,
            "sender": sender,
            "recipient": recipient,
            "message_id": message_id or str(uuid.uuid4()),
            "timestamp": os.time()
        }
    
    @staticmethod
    def create_response(
        original_message: Dict[str, Any],
        success: bool,
        data: Dict[str, Any],
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建响应消息
        
        Args:
            original_message: 原始消息
            success: 是否成功
            data: 响应数据
            error: 错误信息，成功时为None
            
        Returns:
            Dict[str, Any]: 响应消息格式
        """
        return {
            "message_type": ModCommunicationProtocol.MESSAGE_TYPE_RESPONSE,
            "topic": original_message.get("topic", ModCommunicationProtocol.TOPIC_CORE),
            "action": original_message.get("action", ""),
            "data": data,
            "sender": original_message.get("recipient", "core"),
            "recipient": original_message.get("sender"),
            "message_id": original_message.get("message_id"),
            "timestamp": os.time(),
            "success": success,
            "error": error
        }
