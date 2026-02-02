"""
mod管理库，实现mod的扫描、加载、启动和停止功能
"""
import os
import sys
import importlib
import importlib.util
import logging
from typing import Dict, List, Optional, Any
from .mod_interface import ModInterface, ModHostAPI, ModCommunicationProtocol

class ModManager:
    """
    mod管理器，负责mod的扫描、加载、启动和停止
    """
    
    def __init__(self, main_app: Any):
        """
        初始化mod管理器
        
        Args:
            main_app: 主应用程序实例
        """
        self.main_app = main_app
        self.mods_dir = os.path.join(os.path.dirname(__file__), "mods")
        self.loaded_mods: Dict[str, Dict[str, Any]] = {}
        self.host_api = ModHostAPI(main_app)
        self.host_api.set_mod_manager(self)
        self.logger = logging.getLogger("mod.manager")
        
        # 确保mods目录存在
        self._ensure_mods_dir_exists()
    
    def _ensure_mods_dir_exists(self):
        """
        确保mods目录存在
        """
        if not os.path.exists(self.mods_dir):
            os.makedirs(self.mods_dir)
            self.logger.info(f"创建mods目录: {self.mods_dir}")
    
    def scan_mods(self) -> List[str]:
        """
        扫描mods目录中的mod
        
        Returns:
            List[str]: 发现的mod列表
        """
        mods = []
        
        if not os.path.exists(self.mods_dir):
            self.logger.warning(f"mods目录不存在: {self.mods_dir}")
            return mods
        
        for item in os.listdir(self.mods_dir):
            item_path = os.path.join(self.mods_dir, item)
            
            # 检查是否为目录
            if os.path.isdir(item_path):
                # 检查是否包含__init__.py文件
                if os.path.exists(os.path.join(item_path, "__init__.py")):
                    mods.append(item)
                    self.logger.debug(f"发现mod目录: {item}")
            
            # 检查是否为.py文件
            elif item.endswith(".py"):
                mods.append(item[:-3])  # 移除.py后缀
                self.logger.debug(f"发现mod文件: {item}")
        
        self.logger.info(f"共发现 {len(mods)} 个mod")
        return mods
    
    def load_mod(self, mod_name: str) -> bool:
        """
        加载指定的mod
        
        Args:
            mod_name: mod名称
            
        Returns:
            bool: 加载是否成功
        """
        try:
            # 检查mod是否已加载
            if mod_name in self.loaded_mods:
                self.logger.warning(f"mod {mod_name} 已加载")
                return True
            
            # 构建mod路径
            mod_path = os.path.join(self.mods_dir, mod_name)
            
            # 处理目录形式的mod
            if os.path.isdir(mod_path):
                mod_file = os.path.join(mod_path, "__init__.py")
                spec = importlib.util.spec_from_file_location(mod_name, mod_file)
            
            # 处理文件形式的mod
            elif os.path.exists(f"{mod_path}.py"):
                mod_file = f"{mod_path}.py"
                spec = importlib.util.spec_from_file_location(mod_name, mod_file)
            
            else:
                self.logger.error(f"mod {mod_name} 不存在")
                return False
            
            if not spec or not spec.loader:
                self.logger.error(f"无法创建mod {mod_name} 的模块规范")
                return False
            
            # 加载模块
            mod_module = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod_module
            spec.loader.exec_module(mod_module)
            
            # 查找并实例化ModInterface子类
            mod_class = None
            for name, obj in mod_module.__dict__.items():
                if (isinstance(obj, type) and 
                    issubclass(obj, ModInterface) and 
                    obj != ModInterface):
                    mod_class = obj
                    break
            
            if not mod_class:
                self.logger.error(f"mod {mod_name} 中未找到ModInterface的子类")
                return False
            
            # 实例化mod
            # 假设mod类的构造函数接受mod_id, mod_name, mod_version参数
            # 从模块中获取这些信息，如果没有则使用默认值
            mod_id = getattr(mod_module, "MOD_ID", mod_name)
            mod_display_name = getattr(mod_module, "MOD_NAME", mod_name)
            mod_version = getattr(mod_module, "MOD_VERSION", "1.0.0")
            
            mod_instance = mod_class(mod_id, mod_display_name, mod_version)
            
            # 调用on_load方法
            if not mod_instance.on_load(self.host_api):
                self.logger.error(f"mod {mod_name} 加载失败")
                return False
            
            # 存储mod信息
            self.loaded_mods[mod_id] = {
                "name": mod_name,
                "instance": mod_instance,
                "module": mod_module,
                "is_running": False
            }
            
            self.logger.info(f"mod {mod_name} 加载成功")
            return True
            
        except Exception as e:
            self.logger.error(f"加载mod {mod_name} 时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def unload_mod(self, mod_id: str) -> bool:
        """
        卸载指定的mod
        
        Args:
            mod_id: mod唯一标识符
            
        Returns:
            bool: 卸载是否成功
        """
        try:
            if mod_id not in self.loaded_mods:
                self.logger.warning(f"mod {mod_id} 未加载")
                return False
            
            mod_info = self.loaded_mods[mod_id]
            mod_instance = mod_info["instance"]
            
            # 如果mod正在运行，先停止
            if mod_info["is_running"]:
                if not self.stop_mod(mod_id):
                    self.logger.warning(f"停止mod {mod_id} 失败")
            
            # 调用on_unload方法
            if not mod_instance.on_unload():
                self.logger.error(f"mod {mod_id} 卸载失败")
                return False
            
            # 从sys.modules中移除
            mod_name = mod_info["name"]
            if mod_name in sys.modules:
                del sys.modules[mod_name]
            
            # 从加载列表中移除
            del self.loaded_mods[mod_id]
            
            self.logger.info(f"mod {mod_id} 卸载成功")
            return True
            
        except Exception as e:
            self.logger.error(f"卸载mod {mod_id} 时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def start_mod(self, mod_id: str) -> bool:
        """
        启动指定的mod
        
        Args:
            mod_id: mod唯一标识符
            
        Returns:
            bool: 启动是否成功
        """
        try:
            if mod_id not in self.loaded_mods:
                self.logger.warning(f"mod {mod_id} 未加载")
                return False
            
            mod_info = self.loaded_mods[mod_id]
            if mod_info["is_running"]:
                self.logger.warning(f"mod {mod_id} 已经在运行")
                return True
            
            mod_instance = mod_info["instance"]
            
            if not mod_instance.on_start():
                self.logger.error(f"mod {mod_id} 启动失败")
                return False
            
            # 更新状态
            mod_info["is_running"] = True
            mod_instance.is_running = True
            
            self.logger.info(f"mod {mod_id} 启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"启动mod {mod_id} 时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def stop_mod(self, mod_id: str) -> bool:
        """
        停止指定的mod
        
        Args:
            mod_id: mod唯一标识符
            
        Returns:
            bool: 停止是否成功
        """
        try:
            if mod_id not in self.loaded_mods:
                self.logger.warning(f"mod {mod_id} 未加载")
                return False
            
            mod_info = self.loaded_mods[mod_id]
            if not mod_info["is_running"]:
                self.logger.warning(f"mod {mod_id} 已经停止")
                return True
            
            mod_instance = mod_info["instance"]
            
            if not mod_instance.on_stop():
                self.logger.error(f"mod {mod_id} 停止失败")
                return False
            
            # 更新状态
            mod_info["is_running"] = False
            mod_instance.is_running = False
            
            self.logger.info(f"mod {mod_id} 停止成功")
            return True
            
        except Exception as e:
            self.logger.error(f"停止mod {mod_id} 时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def load_all_mods(self) -> Dict[str, bool]:
        """
        加载所有mod
        
        Returns:
            Dict[str, bool]: 各mod的加载结果
        """
        mods = self.scan_mods()
        results = {}
        
        for mod in mods:
            results[mod] = self.load_mod(mod)
        
        return results
    
    def start_all_mods(self) -> Dict[str, bool]:
        """
        启动所有已加载的mod
        
        Returns:
            Dict[str, bool]: 各mod的启动结果
        """
        results = {}
        
        for mod_id in self.loaded_mods:
            results[mod_id] = self.start_mod(mod_id)
        
        return results
    
    def stop_all_mods(self) -> Dict[str, bool]:
        """
        停止所有已加载的mod
        
        Returns:
            Dict[str, bool]: 各mod的停止结果
        """
        results = {}
        
        for mod_id in self.loaded_mods:
            results[mod_id] = self.stop_mod(mod_id)
        
        return results
    
    def unload_all_mods(self) -> Dict[str, bool]:
        """
        卸载所有mod
        
        Returns:
            Dict[str, bool]: 各mod的卸载结果
        """
        results = {}
        
        # 复制一份mod_id列表，因为在循环中会修改loaded_mods
        mod_ids = list(self.loaded_mods.keys())
        
        for mod_id in mod_ids:
            results[mod_id] = self.unload_mod(mod_id)
        
        return results
    
    def send_message(self, mod_id: str, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        发送消息到指定mod
        
        Args:
            mod_id: mod唯一标识符
            message: 消息内容
            
        Returns:
            Optional[Dict[str, Any]]: 回复消息，无回复则返回None
        """
        if mod_id not in self.loaded_mods:
            self.logger.warning(f"mod {mod_id} 未加载")
            return None
        
        try:
            mod_instance = self.loaded_mods[mod_id]["instance"]
            return mod_instance.handle_message(message)
        except Exception as e:
            self.logger.error(f"发送消息到mod {mod_id} 时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def broadcast_message(self, message: Dict[str, Any]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        发送消息到所有已加载的mod
        
        Args:
            message: 消息内容
            
        Returns:
            Dict[str, Optional[Dict[str, Any]]]: 各mod的回复消息
        """
        results = {}
        
        for mod_id in self.loaded_mods:
            results[mod_id] = self.send_message(mod_id, message)
        
        return results
    
    def get_mod_info(self, mod_id: str) -> Optional[Dict[str, Any]]:
        """
        获取mod信息
        
        Args:
            mod_id: mod唯一标识符
            
        Returns:
            Optional[Dict[str, Any]]: mod信息，未找到则返回None
        """
        if mod_id not in self.loaded_mods:
            return None
        
        mod_info = self.loaded_mods[mod_id]
        instance = mod_info["instance"]
        
        return {
            "mod_id": mod_id,
            "name": mod_info["name"],
            "is_running": mod_info["is_running"],
            "mod_specific_info": instance.get_info()
        }
    
    def get_all_mods_info(self) -> List[Dict[str, Any]]:
        """
        获取所有已加载mod的信息
        
        Returns:
            List[Dict[str, Any]]: 所有mod的信息列表
        """
        return [self.get_mod_info(mod_id) for mod_id in self.loaded_mods if self.get_mod_info(mod_id)]
    
    def get_mods_directory(self) -> str:
        """
        获取mods目录路径
        
        Returns:
            str: mods目录路径
        """
        return self.mods_dir
    
    def open_mods_directory(self) -> bool:
        """
        打开mods目录
        
        Returns:
            bool: 操作是否成功
        """
        try:
            import subprocess
            
            # 确保mods目录存在
            self._ensure_mods_dir_exists()
            
            # 打开目录
            if sys.platform == "win32":
                subprocess.run(["explorer", self.mods_dir], check=True)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.mods_dir], check=True)
            else:
                subprocess.run(["xdg-open", self.mods_dir], check=True)
            
            self.logger.info(f"已打开mods目录: {self.mods_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"打开mods目录时发生错误: {str(e)}")
            return False
    
    def remove_mod(self, mod_name: str) -> bool:
        """
        移除指定的mod
        
        Args:
            mod_name: mod名称
            
        Returns:
            bool: 移除是否成功
        """
        try:
            # 构建mod路径
            mod_path = os.path.join(self.mods_dir, mod_name)
            
            # 检查mod是否存在
            if os.path.isdir(mod_path):
                # 移除目录
                import shutil
                shutil.rmtree(mod_path)
                self.logger.info(f"已移除mod目录: {mod_name}")
            elif os.path.exists(f"{mod_path}.py"):
                # 移除文件
                os.remove(f"{mod_path}.py")
                self.logger.info(f"已移除mod文件: {mod_name}.py")
            else:
                self.logger.warning(f"mod {mod_name} 不存在")
                return False
            
            # 如果mod已加载，卸载它
            # 查找对应的mod_id
            mod_id_to_unload = None
            for mod_id, mod_info in self.loaded_mods.items():
                if mod_info["name"] == mod_name:
                    mod_id_to_unload = mod_id
                    break
            
            if mod_id_to_unload:
                self.unload_mod(mod_id_to_unload)
            
            return True
            
        except Exception as e:
            self.logger.error(f"移除mod {mod_name} 时发生错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
