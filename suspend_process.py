import psutil, ctypes, platform

def suspend_process_with_NtSuspendProcess(pid) -> bool:
        # 定义 Windows API
        kernel32 = ctypes.WinDLL('kernel32')
        ntdll = ctypes.WinDLL('ntdll')
        PROCESS_SUSPEND_RESUME = 0x0800
        h_process = kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)

        if not h_process:
            return False

        # 挂起进程
        status = ntdll.NtSuspendProcess(h_process)
        kernel32.CloseHandle(h_process)
        return status == 0

def suspend_process_with_psutil_lib(pid) -> bool:
    try:
        p = psutil.Process(pid)
        p.suspend()  # 挂起进程
        return True
    except Exception:
        return False

def suspend_process(pid, nt_first: bool = False):
    """
    挂起指定进程
    Parameters:
        pid(int):
            目标进程 PID
        nt_first(bool):
            是否优先使用 NtSuspendProcess
    Returns:
        bool:
            目标进程是否挂起成功
    """
    if not platform.machine().endswith('64'):
        return False
    if nt_first:
        # 若指定，则优先使用 NtSuspendProcess
        if suspend_process_with_NtSuspendProcess(pid):
            return True
        return suspend_process_with_psutil_lib(pid)
    # 若未指定，则优先使用 psutil库
    if suspend_process_with_psutil_lib(pid):
        return True
    return suspend_process_with_NtSuspendProcess(pid)

def resume_process_with_NtResumeProcess(pid) -> bool:
    # 定义 Windows API
    kernel32 = ctypes.WinDLL('kernel32')
    ntdll = ctypes.WinDLL('ntdll')
    PROCESS_SUSPEND_RESUME = 0x0800
    h_process = kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)

    if not h_process:
        return False

    # 取消挂起进程
    status = ntdll.NtResumeProcess(h_process)
    kernel32.CloseHandle(h_process)
    return status == 0

def resume_process_with_psutil_lib(pid) -> bool:
    try:
        p = psutil.Process(pid)
        p.resume()  # 取消挂起进程
        return True
    except Exception:
        return False

def resume_process(pid, nt_first: bool = False):
    """
    取消挂起指定进程
    Parameters:
        pid(int):
            目标进程 PID
        nt_first(bool):
            是否优先使用 NtSuspendProcess
    Returns:
        bool:
            目标进程是否取消挂起成功
    """
    if not platform.machine().endswith('64'):
        return False
    if nt_first:
        # 若指定，则优先使用 NtSuspendProcess
        if resume_process_with_NtResumeProcess(pid):
            return True
        return resume_process_with_psutil_lib(pid)
    # 若未指定，则优先使用 psutil库
    if resume_process_with_psutil_lib(pid):
        return True
    return resume_process_with_NtResumeProcess(pid)


if __name__ == '__main__':
    suspend_process(11792)
    input("按回车键继续")
    resume_process(11792)
