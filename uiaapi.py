import os
import ctypes
from ctypes import wintypes
def load_uia():
    # 加载uiaccess.dll
    uiaccess = ctypes.WinDLL(os.path.join(os.path.dirname(__file__), 'uia.dll'), use_last_error=True)

    # 定义函数原型
    IsProcessElevated = uiaccess.IsProcessElevated
    IsProcessElevated.argtypes = [wintypes.HANDLE]
    IsProcessElevated.restype = wintypes.BOOL

    IsUIAccess = uiaccess.IsUIAccess
    IsUIAccess.argtypes = []
    IsUIAccess.restype = wintypes.BOOL

    StartUIAccessProcess = uiaccess.StartUIAccessProcess
    StartUIAccessProcess.argtypes = [
        wintypes.LPCWSTR,  # lpApplicationName
        wintypes.LPCWSTR,  # lpCommandLine
        wintypes.DWORD,    # flag
        ctypes.POINTER(wintypes.DWORD),  # pPid
        wintypes.DWORD     # dwSession
    ]
    StartUIAccessProcess.restype = wintypes.BOOL

    GetLastError = ctypes.windll.kernel32.GetLastError
    GetLastError.restype = wintypes.DWORD

    return uiaccess, IsUIAccess, StartUIAccessProcess

# 获取当前会话ID的函数
def get_current_session_id():
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    
    # 定义函数原型
    GetCurrentProcessId = kernel32.GetCurrentProcessId
    GetCurrentProcessId.argtypes = []
    GetCurrentProcessId.restype = wintypes.DWORD
    
    ProcessIdToSessionId = kernel32.ProcessIdToSessionId
    ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    ProcessIdToSessionId.restype = wintypes.BOOL
    
    # 获取当前进程ID
    pid = GetCurrentProcessId()
    
    # 获取会话ID
    session_id = wintypes.DWORD(0)
    if not ProcessIdToSessionId(pid, ctypes.byref(session_id)):
        raise ctypes.WinError(ctypes.get_last_error())
    
    return session_id.value
