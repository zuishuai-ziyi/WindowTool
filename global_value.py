import os, traceback, enum
from log import Log as LogClass
from api import get_file_path
from operation_profile import Profile as ProfileClass, TypeIgnore

class ExitCode(enum.IntEnum):
    '''退出代码'''
    SUCCESS = 0
    UNKNOWN_ERROR = 1
    RESTART = 2


# 初始化日志文件对象
os.makedirs(get_file_path('temp'), exist_ok=True)
log = LogClass(output_to_file=get_file_path("temp\\log.log"))

# 读取配置文件
profile_obj = ProfileClass(get_file_path("data\\profile\\data.yaml"))
_default_profile = \
{
    'set_up': {
        'on_top_time': -1.0,                # 强制置顶间隔时间
        'on_top_with_UIAccess': True,       # 是否启用 UIAccess 超级置顶
        'keep_work_time': -1.0,             # 强制前台间隔时间
        'start_choose_window_hotkey': [     # 启动选择窗口热键
            'ctrl', 'alt', 'd'
        ],
        'allow_hotkey_start_choose': True,  # 是否允许使用快捷键开始选择窗口
        'show_info_box': True,              # 是否显示信息文本框
        'show_warning_box': True,           # 是否显示警告文本框
        'show_error_box': True,             # 是否显示错误文本框
        'show_tray_icon': True              # 是否显示托盘图标
    },
    'select_window_info': TypeIgnore([])
}
# 设置默认值
profile_obj.set_default(_default_profile)
if not profile_obj.check_file():
    log("配置文件不存在或存在错误，尝试重置...")
    if profile_obj.file_exists():
        os.remove(get_file_path("data\\profile\\data.yaml"))
    try:
        profile_obj.create(_default_profile)
        log("重置成功")
    except Exception:
        log.warning(f"重置配置文件时发生异常:\n{traceback.format_exc()}")
        os._exit(0)
