import win32gui, win32api, win32process, win32con, os, sys, ctypes, traceback
from ctypes import wintypes
from pathlib import Path
from global_value import *

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
    return str(
            Path(
                sys._MEIPASS if hasattr(sys, '_MEIPASS') else __file__  # type: ignore
            ).parent.resolve() / Path(file_path)
    )

def load_uia_lib():
    '''加载 uia.dll'''
    try:
        lib_name = 'uia.dll'
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
        log.warning(f'加载 {lib_name} 失败:\n{traceback.format_exc()}')
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
