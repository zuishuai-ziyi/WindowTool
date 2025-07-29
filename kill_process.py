import ctypes, platform

def kill_process_with_terminate(pid) -> bool:
    '''使用 TerminateProcess 终止进程'''
    # 尝试加载dll
    try:
        kernel32 = ctypes.WinDLL('kernel32')
    except OSError:
        return False

    # 定义常量
    PROCESS_TERMINATE = 0x0001

    # 打开进程
    hProcess = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not hProcess:
        return False

    # 使用 TerminateProcess 终止进程
    status = kernel32.TerminateProcess(hProcess, 0)
    kernel32.CloseHandle(hProcess)
    return bool(status)

def kill_process_with_NtTerminate(pid) -> bool:
    '''使用 NtTerminateProcess 终止进程'''
    # 尝试加载dll
    try:
        ntdll = ctypes.WinDLL('ntdll')
        kernel32 = ctypes.WinDLL('kernel32')
    except OSError:
        return False

    # 定义常量
    PROCESS_TERMINATE = 0x0001
    STATUS_SUCCESS = 0x00000000

    # 打开进程
    hProcess = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not hProcess:
        return False

    # 使用 NtTerminateProcess 终止进程
    status = ntdll.NtTerminateProcess(hProcess, 0)
    kernel32.CloseHandle(hProcess)

    return status == STATUS_SUCCESS

def kill_process(pid: int, Nt_first: bool = False) -> bool:
    """
    终止指定进程
    Parameters:
        pid(int):
            目标进程 PID
    Returns:
        bool:
            目标进程是否终止成功
    """
    if not platform.machine().endswith('64'):
        return False
    if Nt_first:
        # 若指定，则优先使用 NtTerminateProcess
        if kill_process_with_NtTerminate(pid):
            return True
        return kill_process_with_terminate(pid)
    # 若未指定，则优先使用 TerminateProcess
    if kill_process_with_terminate(pid):
        return True
    return kill_process_with_NtTerminate(pid)



if __name__ == "__main__":
    current_pid = 0
    print(f"目标进程PID: {current_pid}")

    if kill_process(current_pid):
        print(f"成功终止进程 {current_pid}")
    else:
        print(f"无法终止进程 {current_pid}")
