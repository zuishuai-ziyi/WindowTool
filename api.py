import win32gui, win32api, win32process, win32con, os, sys, ctypes, traceback, hashlib
from ctypes import wintypes
from pathlib import Path
from typing import Callable, Iterable, Any
import global_value

# UIAccess.dll 验证信息
UIAccess_DLL_INFO = {
    'size': 209920,  # 文件大小（字节）
    'hashes': {
        'md5': '07754cba334563479c95fefb72ca14d1',
        'sha1': '42995c367c6f57909a0d24704f432a4308979d4c',
        'sha224': 'f62bba41d17d2b191f3c65b954a86bebb6d0d954f2a3750f8fa53db9',
        'sha256': '8b4ec1ae7fd69d314100e0c0556d45a87b40576f4d1819ddc5880c6ef00501de',
        'sha384': '1275489a65467926dc8e761802adb182d064b1b263749a5187b227bffde64bb4f5e6855fb821757dd7e306af65c8bcf3',
        'sha512': '37ee6705601c5ea293566862894bfaea7fab7c53d6867cf725e7b13a00a7e1f1768939c4eae3747e1b0472bb226de08c2babdfcd52a1859a0214cc0b929f088f',
        'blake2b': '56e50d7eb97eea68b3d23b705639169cb25f5dce23b9584d9a517d882d82029d3f9b5a1f508bd69ae7cb32c4dbeb42370e45ef63d7504f5d82098f03c291a11b',
        'blake2s': '41f95fe1c7e20ddc23be1fe7dc3e11afebed53ae7b0449cbdae84b26d1731ee5',
        'sha3_224': '8800138effefc64f09465eaf777c74698de1cb0c74ef29e937fbfcaf',
        'sha3_256': '79dd4211a744dc850a8880f66ea84e6ee5cf9b251a231a2e86b6fad4912a5a3c'
    }
}

# 官方下载地址
OFFICIAL_DOWNLOAD_URL = 'https://xiaoziyi.com/project/1'

def get_top_window_under_mouse(exclude_hwnds: list[int] | None = None) -> tuple[int, int]:
    '''获取鼠标处顶层窗口PID及句柄'''
    if exclude_hwnds is None:
        exclude_hwnds = []

    x, y = win32api.GetCursorPos()

    # 使用更可靠的函数获取窗口
    hwnd = win32gui.WindowFromPoint((x, y))

    # 使用父窗口查找
    hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)

    # 排除指定窗口
    while hwnd and hwnd in exclude_hwnds:
        # 尝试获取下一个窗口
        next_hwnd = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)
        
        # 检查下一个窗口是否在相同位置
        if not next_hwnd:
            return (0, 0)

        left, top, right, bottom = win32gui.GetWindowRect(next_hwnd)
        if not(left <= x <= right and top <= y <= bottom):
            return (0, 0)
        hwnd = next_hwnd

    # 获取顶层窗口
    parent = hwnd
    while True:
        next_parent = win32gui.GetParent(parent)
        if next_parent == 0:
            break
        parent = next_parent

    top_hwnd = parent
    pid = win32process.GetWindowThreadProcessId(top_hwnd)[1]
    return (pid, top_hwnd)

def get_window_pos_and_size(hwnd) -> tuple[int, int, int, int, int, int]:
        '''获取窗口位置和尺寸信息 返回值格式：left, top, right, bottom, width, height'''
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width, height = right - left, bottom - top
        return left, top, right, bottom, width, height

def get_file_path(file_path: str):
    """获取资源文件实际绝对路径"""
    file_abs_path = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(__file__).parent # type: ignore
    return str(
        file_abs_path.resolve() / Path(file_path)
    )

def verify_UIAccess_dll():
    '''验证 UIAccess.dll 的完整性'''
    try:
        lib_name = 'UIAccess.dll'
        dll_path = get_file_path(lib_name)
        
        # 检查文件是否存在
        if not os.path.exists(dll_path):
            global_value.log.error(f'文件 {lib_name} 不存在')
            return False, f'文件 {lib_name} 不存在'
        
        # 检查文件大小
        file_size = os.path.getsize(dll_path)
        if file_size != UIAccess_DLL_INFO['size']:
            global_value.log.error(f'文件 {lib_name} 大小不匹配: 实际 {file_size} 字节, 预期 {UIAccess_DLL_INFO["size"]} 字节')
            return False, f'文件 {lib_name} 大小不匹配'
        
        # 读取文件内容
        with open(dll_path, 'rb') as f:
            file_content = f.read()
        
        # 计算并验证哈希值
        hash_methods = {
            'md5': hashlib.md5,
            'sha1': hashlib.sha1,
            'sha224': hashlib.sha224,
            'sha256': hashlib.sha256,
            'sha384': hashlib.sha384,
            'sha512': hashlib.sha512,
            'blake2b': hashlib.blake2b,
            'blake2s': hashlib.blake2s,
            'sha3_224': hashlib.sha3_224,
            'sha3_256': hashlib.sha3_256,
        }
        
        for name, method in hash_methods.items():
            hash_obj = method(file_content)
            calculated_hash = hash_obj.hexdigest()
            expected_hash = UIAccess_DLL_INFO['hashes'][name]
            if calculated_hash != expected_hash:
                global_value.log.error(f'文件 {lib_name} {name} 哈希值不匹配')
                return False, f'文件 {lib_name} {name} 哈希值不匹配'
        
        # 所有验证通过
        global_value.log.info(f'文件 {lib_name} 验证通过')
        return True, '验证通过'
        
    except Exception as e:
        global_value.log.error(f'验证 {lib_name} 时发生错误:\n{traceback.format_exc()}')
        return False, f'验证时发生错误: {str(e)}'

def load_UIAccess_lib():
    '''加载 UIAccess.dll'''
    try:
        lib_name = 'UIAccess.dll'
        
        # 验证文件完整性
        is_valid, message = verify_UIAccess_dll()
        if not is_valid:
            # 显示错误消息框
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(None, "错误", f"{message}\n\n请从官方地址下载正确的文件:\n{OFFICIAL_DOWNLOAD_URL}")
            return None
        
        # 验证通过，加载 DLL
        UIAccessLib = ctypes.WinDLL(get_file_path(lib_name), use_last_error=True)

        # 定义函数原型
        IsUIAccess = UIAccessLib.IsUIAccess
        IsUIAccess.argtypes = []
        IsUIAccess.restype = wintypes.BOOL

        StartUIAccessProcess = UIAccessLib.StartUIAccessProcess
        StartUIAccessProcess.argtypes = [
            wintypes.LPCWSTR,  # lpApplicationName
            wintypes.LPCWSTR,  # lpCommandLine
            wintypes.DWORD,    # flag
            ctypes.POINTER(wintypes.DWORD),  # pPid
            wintypes.DWORD     # dwSession
        ]
        StartUIAccessProcess.restype = wintypes.BOOL
    except Exception:
        global_value.log.warning(f'加载 {lib_name} 失败:\n{traceback.format_exc()}')
        return None
    return UIAccessLib, IsUIAccess, StartUIAccessProcess

def get_session_id() -> int:
    '''获取当前会话的ID'''
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    
    # 定义函数原型
    ProcessIdToSessionId = kernel32.ProcessIdToSessionId
    ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    ProcessIdToSessionId.restype = wintypes.BOOL

    # 获取会话ID
    session_id = wintypes.DWORD(0)
    if not ProcessIdToSessionId(os.getpid(), ctypes.byref(session_id)):
        raise ctypes.WinError(ctypes.get_last_error())

    return session_id.value

def deep_search(data: Iterable, callback: Callable[[list[str | int]], Any], now_path: list[str | int] | None = None, always_call_callback: bool = False):
    """深度遍历数据结构，执行回调函数 always_call_callback -> 对于可迭代对象，仍然调用回调函数"""
    if now_path is None:
        # 初始化路径
        now_path = []
    else:
        # 复制路径
        now_path = now_path.copy()
    # 边界判断
    if (not isinstance(data, Iterable)) or isinstance(data, str):
        callback(now_path)
        return
    # 检测是否调用回调函数
    if always_call_callback and now_path:
        callback(now_path)
    # 初始化索引
    now_path.append(-1)
    # 遍历字典
    if isinstance(data, dict):
        for k, v in data.items():
            now_path[-1] = k  # 更新当前路径
            deep_search(v, callback, now_path, always_call_callback)
        return
    # 遍历其他可迭代对象
    for i, item in enumerate(data):
        now_path[-1] = i  # 更新当前路径
        deep_search(item, callback, now_path, always_call_callback)
    return

def get_value_from_path[DefaultType: Any](data: dict, path: list[str | int], default: DefaultType = None) -> Any | DefaultType:
    """根据路径获取字典中的值"""
    cdata = data.copy()
    for key in path:
        if isinstance(cdata, dict):
            if key in cdata:
                cdata = cdata[key]
            else:
                return default
        elif isinstance(cdata, list):
            if isinstance(key, int) and 0 <= key < len(cdata):
                cdata = cdata[key]
            else:
                return default
        else:
            break
    return cdata

if __name__ == "__main__":
    # 测试深度遍历
    test_data = {
        'a': [1, 2, {'b': 3, 'c': [4, 5]}],
        'd': {'e': 6, 'f': [7, 8]}
    }
    deep_search(test_data, lambda path: print(path, get_value_from_path(test_data, path)), always_call_callback=True)
