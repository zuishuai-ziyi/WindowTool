import ctypes
from other_window import MessageBox
from PyQt5.QtWidgets import QMessageBox
from typing import Any

# 正确定义函数原型
kernel32 = ctypes.WinDLL('kernel32.dll', use_last_error=True)

# 定义LoadLibraryW
LoadLibraryW = kernel32.LoadLibraryW
LoadLibraryW.argtypes = [ctypes.c_wchar_p]
LoadLibraryW.restype = ctypes.c_void_p  # HMODULE是void指针

# 定义GetProcAddress
GetProcAddress = kernel32.GetProcAddress
GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_void_p]  # 接受整数资源ID
GetProcAddress.restype = ctypes.c_void_p

# 加载DLL
shell32 = LoadLibraryW('shell32.dll')

# 获取函数地址 (61作为资源ID)
func_address = GetProcAddress(shell32, ctypes.c_void_p(61))
RunFileDlg_win32 = None

# 将地址转换为函数指针
if func_address:
    # 定义函数原型
    FUNCTYPE = ctypes.WINFUNCTYPE(
        ctypes.c_int,      # 返回值类型
        ctypes.c_void_p,   # hwndOwner
        ctypes.c_void_p,   # hIcon
        ctypes.c_wchar_p,  # lpstrDirectory
        ctypes.c_wchar_p,  # lpstrTitle
        ctypes.c_wchar_p,  # lpstrDescription
        ctypes.c_int       # uFlags
    )

    # 创建可调用的函数对象
    RunFileDlg_win32 = FUNCTYPE(func_address)

else:
    RunFileDlg_win32 = None
    print("Failed to get function address")

def ShowRunDialog(hwndOwner, hIcon, lpstrDirectory, lpstrTitle, lpstrDescription, uFlags) -> bool:
    if RunFileDlg_win32 is None:
        return False
    RunFileDlg_win32(int(hwndOwner), hIcon, lpstrDirectory, lpstrTitle, lpstrDescription, uFlags)
    return True

if __name__ == '__main__':
        print(f"Function address: {hex(func_address)}")
