import ctypes, os

def delete_file(path: str) -> bool:
    print(f"[TRACE] 删除文件: {path}")
    if not os.path.exists(path):
        return False

    try:

        # 设置文件属性为普通
        FILE_ATTRIBUTE_NORMAL = 0x80
        ctypes.windll.kernel32.SetFileAttributesW(path, FILE_ATTRIBUTE_NORMAL)

        # 调用 DeleteFile API 删除文件
        return bool(ctypes.windll.kernel32.DeleteFileW(path))

    except:
        print(f"[ERROR] 删除文件失败: {path}")
        return False

if __name__ == "__main__":
    import kill_process
    kill_process.kill_process(11836)
    res = delete_file("D:\\desktop\\main - 副本.exe")
    print(res)
