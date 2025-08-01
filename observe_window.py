import re
import win32gui
import win32con
import threading
import time
import atexit, traceback
from api import get_window_pos_and_size
from typing import Callable, Self

class ObserverError(Exception):
    '''观察器错误'''
    ...

class StatusError(ObserverError):
    '''状态错误：当前状态不能进行此操作'''
    ...

class ObserveWindow:
    def __init__(self, hwnd: int, callback: Callable, wait_time: float = 0.01) -> None:
        self._window_hwnd = hwnd
        self._window_info = self._get_window_info()
        '''记录的窗口信息'''
        self._is_observing = False
        '''是否正在观察窗口变化'''
        self._wait_time = wait_time
        '''观察间隔时间'''
        self._callback = callback
        '''窗口信息变化时的回调函数'''

        self._IsWindow = lambda hwnd: isinstance(hwnd, int) and win32gui.IsWindow(hwnd)
    
    def start(self):
        if self._is_observing:
            raise StatusError("已在观察窗口")
        # 更新状态
        self._is_observing = True
        # 启动观察
        thread_obj = threading.Thread(target=self._observe_func)
        thread_obj.start()


    def stop(self):
        if not self._is_observing:
            raise StatusError("无法在未观察窗口时停止")
        # 更新状态
        self._is_observing = False

    def _observe_func(self):
        '''观察窗口变化，运行在单独线程中'''
        while self._is_observing:
            if not self._IsWindow(self._window_hwnd):
                # 目标窗口无效，停止观察
                self.stop()
                return
            now_window_info = self._get_window_info()
            for k, v in now_window_info.items():
                if v != self._window_info[k]:
                    self._callback(
                        self._window_info,
                        now_window_info
                    )
                    break
            self._window_info = now_window_info
            time.sleep(self._wait_time)
    
    def is_observing(self) -> bool:
        return self._is_observing

    def __enter__(self) -> Self:
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if not self._is_observing:
            # 资源已被释放
            return False
        self.stop()
        if exc_type is Exception and issubclass(exc_type, ObserverError):
            # 观察器错误，忽略错误并打印警告
            print(f"[WARNING] 观察器错误，详细错误信息如下: ")
            traceback.print_tb(exc_tb)
            print(f"  {exc_type.__name__}: {exc_val}")
            return True
        return False

    def _get_window_info(self):
        '''获取当前窗口现在的信息'''
        left, top, right, bottom, width, height = get_window_pos_and_size(self._window_hwnd)
        return {
            'pos': [left, top],
            'size': [width, height],
            'title': win32gui.GetWindowText(self._window_hwnd)
        }

if __name__ == '__main__':
    with ObserveWindow(199238, lambda old, now: print(old, now)) as obj:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            ...
