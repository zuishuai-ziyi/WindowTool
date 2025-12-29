from transparent_overlay_window import TransparentOverlayWindow as TOW
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QFormLayout, QHBoxLayout, QDialog, QLineEdit, QCheckBox, QSizePolicy, QSystemTrayIcon, QMenu, QListWidget, QListWidgetItem, QTableView
from PyQt5.QtGui import QCloseEvent, QIcon, QDoubleValidator, QFontMetrics, QStandardItemModel, QStandardItem
from PyQt5.QtCore import QEvent, Qt, QTimer, pyqtSignal, QItemSelectionModel
from global_value import *
from api import get_top_window_under_mouse, get_window_pos_and_size, get_file_path, load_UIAccess_lib, get_session_id
from kill_process import kill_process
from delete_file import delete_file
from suspend_process import suspend_process, resume_process
from other_window import input_box_window, MessageBox
from operation_profile import OperationType, OperationData
from observe_window import ObserveWindow
from call_run_dialog import ShowRunDialog
from typing import Any, Dict, Literal, List, Callable, NoReturn, Iterable, overload
from ctypes import wintypes
import sys, win32gui, win32con, win32process, psutil, keyboard, ctypes, os, traceback, pywintypes, time, threading, webbrowser, re, argparse, functools, subprocess


class MainWindow(QWidget):
    '''主窗口'''
    # 热键触发信号，防止 热键触发时的回调函数 中的计时器在另一个线程中开启
    hotkey_triggered = pyqtSignal()
    def __init__(self) -> None:
        super().__init__()

        # 创建计时器，用于在选择时更新窗口信息
        self.update_sele_wind_timer = QTimer(self)
        self.update_sele_wind_timer.timeout.connect(self.slot_of_update_selected_window_info)
        # 创建计时器，用于更新窗口并记录选中窗口信息至文件
        self.update_window_timer = QTimer(self)
        self.update_window_timer.timeout.connect(self.slot_of_update_window)
        # 创建计时器组，用于更新窗口属性
        self.update_window_attribute_timers = {
            "on_top": (
                obj := QTimer(self),
                obj.timeout.connect(self.slot_of_update_on_top)
            )[0],
            "keep_work": (
                obj := QTimer(self),
                obj.timeout.connect(self.slot_of_update_keep_work)
            )[0],
        }

        # 初始化蒙版属性
        self.init_overlay_attribute()

        # 设置窗口标志
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint  # type: ignore
        )

        # 设置窗口图标
        self.setWindowIcon(QIcon(get_file_path('data\\icon\\window.png')))

        # 设置窗口标题
        self.setWindowTitle('WindowTool')

        # 初始化属性
        self.is_getting_info = False
        self.last_on_top_time = time.time()
        self.last_keep_work_time = time.time()
        self.last_sel_window_info = {'pos': None, 'size': None}

        # 设置窗口位置和大小
        screen = app.primaryScreen().availableGeometry() # type: ignore

        width, height = 640, 480
        left, top = (screen.width()-width)//2, (screen.height()-height)//2

        self.setGeometry(left, top, width, height)

        self.IsWindow: Callable[[Any], bool]  = lambda hwnd: bool(isinstance(hwnd, int) and win32gui.IsWindow(hwnd))
        self.IsProcess: Callable[[int], bool] = lambda pid: isinstance(pid, int) and psutil.pid_exists(pid)

        self.main_UI()

        # 启动热键监听
        self.hotkey_triggered.connect(lambda: self.slot_of_start_get_window_button() and None)
        if profile_obj['set_up']['allow_hotkey_start_choose']:
            self.re_register_start_choose_window_hotkey(None)

    def changeEvent(self, event: QEvent | None) -> None:
        if profile_obj.get('set_up').get('allow_minimize', True) == False:
            if event and event.type() == QEvent.WindowStateChange: # type: ignore
                if self.isMinimized() or self.isHidden():
                    self.showNormal() # 防止最小化
        return super().changeEvent(event)

    def main_UI(self) -> None:
        self.select_hwnd = None
        self.select_pid = None
        self.select_obj = None
        '''选中进程的 process 对象'''
        self.observe_obj = None
        '''观察目标窗口的观察器对象'''
        self.is_setting_input_box: Dict[str, bool] = dict(
            (item, False) for item in {'title', 'pos', 'size'}
        )
        '''当前程序是否正在更改某个输入框的文本'''
        self.select_process_info: Dict[str, Any] = {  # 选中进程的其他信息
            'suspend': False,  # 是否挂起
        }
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter) # type: ignore

        # 添加文本
        text = QLabel("点击按钮后，将鼠标移至其他窗口以获取窗口信息")
        main_layout.addWidget(text)

        # 添加 开始获取窗口按钮 布局
        start_get_window_button_layout = QHBoxLayout()
        # 添加 开始获取窗口 按钮
        self.start_get_window_button = QPushButton("开始获取")
        self.start_get_window_button.clicked.connect(self.slot_of_start_get_window_button)
        start_get_window_button_layout.addWidget(self.start_get_window_button)
        # 添加 从窗口列表中获取窗口 按钮
        self.start_get_window_button_from_list = QPushButton("从窗口列表中获取")
        self.start_get_window_button_from_list.clicked.connect(self.slot_of_start_get_window_button_from_list)
        start_get_window_button_layout.addWidget(self.start_get_window_button_from_list)
        # 添加 开始获取窗口按钮 布局 至 主布局
        main_layout.addLayout(start_get_window_button_layout)

        # 添加 窗口数据布局
        self.selec_window_info_layout = QFormLayout()

        # 定义辅助函数
        def get_QLabel_read_only(*args: Any, **kwargs: Any) -> QLabel:
            '''创建可复制的 QLabel '''
            obj = QLabel(*args, **kwargs)
            obj.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard) # type: ignore  # 设置可复制
            obj.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 设置固定大小
            obj.setWordWrap(False)
            return obj
        def get_QLineEdit_read_only(*args: Any, width: int = 85) -> QLineEdit:
            '''创建禁用且固定宽度的 QLineEdit '''
            obj = QLineEdit(*args)
            obj.setFixedWidth(width)
            obj.setEnabled(False)
            return obj

        # 添加窗口数据控件
        default_text: str = '[ 无数据 ]'
        
        self.sel_wind_info_widgets: dict[Literal['window_title'] | Literal['window_exe'] | Literal['window_pos'] | Literal['window_size'] | Literal['process_pid'] | Literal['process_hwnd'], Dict[Any, Any]] = {}
        self.sel_wind_info_widgets['process_pid'] = {
            'display': "进程PID：",
            'obj': get_QLabel_read_only(default_text)
        }
        self.sel_wind_info_widgets['process_hwnd'] = {
            'display': "窗口句柄：",
            'obj': get_QLabel_read_only(default_text)
        }
        self.sel_wind_info_widgets['window_title'] = {
            'display': "窗口标题：",
            'obj': (
                (
                    obj := get_QLineEdit_read_only(default_text, width=300),
                    obj.editingFinished.connect(self.slot_of_size_title_pos_input_box_edit_finished)
                ),
                (obj, )
            )[1]
        }
        self.sel_wind_info_widgets['window_pos'] = {
            'display': "窗口位置：",
            'obj': (
                (  # 初始化
                    x_text := QLabel('x: '),
                    x_text.setFixedWidth(20),
                    y_text := QLabel('y: '),
                    y_text.setFixedWidth(20),
                    x_input_box := get_QLineEdit_read_only(default_text),
                    y_input_box := get_QLineEdit_read_only(default_text),
                    x_input_box.editingFinished.connect(self.slot_of_size_title_pos_input_box_edit_finished),
                    y_input_box.editingFinished.connect(self.slot_of_size_title_pos_input_box_edit_finished),
                ),
                (  # 添加
                    x_text,
                    x_input_box,
                    y_text,
                    y_input_box
                )
            )[1]
        }
        self.sel_wind_info_widgets['window_size'] = {
            'display': "窗口大小：",
            'obj': (
                (  # 初始化
                    w_text := QLabel('宽: '),
                    w_text.setFixedWidth(20),
                    h_text := QLabel('高: '),
                    h_text.setFixedWidth(20),
                    w_input_box := get_QLineEdit_read_only(default_text),
                    h_input_box := get_QLineEdit_read_only(default_text),
                    w_input_box.editingFinished.connect(self.slot_of_size_title_pos_input_box_edit_finished),
                    h_input_box.editingFinished.connect(self.slot_of_size_title_pos_input_box_edit_finished),
                ),
                (  # 添加
                    w_text,
                    w_input_box,
                    h_text,
                    h_input_box
                )
            )[1]
        }
        self.sel_wind_info_widgets['window_exe'] = {
            'display': "可执行文件位置：",
            'obj': get_QLabel_read_only(default_text)
        }

        # 添加控件至 窗口数据布局
        for k in self.sel_wind_info_widgets:
            v = self.sel_wind_info_widgets[k]
            if not isinstance(v['obj'], (list, tuple)):
                # 仅一个控件，直接添加
                self.selec_window_info_layout.addRow(v['display'], v['obj'])
                continue
            # 多个控件，依次添加至水平布局
            t_widget = QWidget()  # 创建临时控件
            t_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # 设置临时控件固定宽高
            t_layout = QHBoxLayout(t_widget)  # 设置布局的父控件为临时控件
            t_layout.setContentsMargins(0, 0, 0, 0)  # 消除边距
            for w in v['obj']:  # 将控件添加至布局
                t_layout.addWidget(w)
            self.selec_window_info_layout.addRow(v['display'], t_widget)  # 将临时控件添加至布局，以确保宽度固定
        # 将 窗口数据布局 添加至 主布局
        main_layout.addLayout(self.selec_window_info_layout)


        # 添加 窗口操作布局
        dos_button_layout = QGridLayout()

        # 添加窗口操作控件
        def _set_attribute(dict_obj: Dict, key: str, value: Any) -> None:
            '''设置属性'''
            dict_obj[key] = value
        def _show_message_box(success: bool, code: int | None = None):
            if success and profile_obj['set_up']['show_info_box']:
                MessageBox(
                    self,
                    top_info="操作成功完成",
                    title="提示",
                    icon=QMessageBox.Information,
                    buttons=("确定", )
                ) if profile_obj['set_up']['show_info_box'] else None
            elif profile_obj['set_up']['show_error_box']:
                MessageBox(
                    self,
                    top_info="尝试执行操作时发生错误",
                    info='' if code is None else f'错误代码: {code}',
                    title="错误",
                    icon=QMessageBox.Critical, buttons=("确定", )
                ) if profile_obj['set_up']['show_error_box'] else None
        max_len_for_1_line = 3  # 单行最大控件数
        dos_buttons: List[List[QPushButton | Callable | Dict[Literal['need'], Dict[Literal['pid'] | Literal['hwnd'], bool]]]] = [
            [
                QPushButton('结束所选进程'),
                lambda pid, hwnd: (
                    kill_process(pid),
                    (MessageBox(self, "已发送终止信号至进程", f'进程PID: {pid}', icon=QMessageBox.Information) if profile_obj['set_up']['show_info_box'] else None)
                )
            ],
            [
                QPushButton('删除所选进程源文件'),
                lambda pid, hwnd: (
                    (
                        kill_success := kill_process(pid),
                        pid_exe := psutil.Process(pid).exe(),
                        handle := ctypes.windll.kernel32.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid),
                        wait_code := ctypes.windll.kernel32.WaitForSingleObject(handle, 3000),  # 等待进程退出，最多等待 3 秒
                        ctypes.windll.kernel32.CloseHandle(handle),
                        success := delete_file(pid_exe),
                        reason := '未能结束选中进程' if kill_success else ('等待进程退出超时' if wait_code == win32con.WAIT_TIMEOUT else '您可能没有适当的权限访问目标文件'),
                        (MessageBox(self, title='删除成功', top_info=f'文件 {pid_exe} 删除成功', icon=QMessageBox.Information) if profile_obj['set_up']['show_info_box'] else None) if success else 
                        (MessageBox(self, title='删除失败', top_info=f'文件 {pid_exe} 删除失败', info=reason, icon=QMessageBox.Critical) if profile_obj['set_up']['show_error_box'] else None)
                    )
                )
            ],
            [
                QPushButton('窗口无边框化/恢复'),
                lambda pid, hwnd: (
                    self.set_window_border(hwnd, None),
                    _show_message_box(True),
                )
            ],
            [
                QPushButton('窗口最小化'),
                lambda pid, hwnd: (
                    res := win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE),
                    _show_message_box(True, res),
                )
            ],
            [
                QPushButton('窗口最大化'),
                lambda pid, hwnd: (
                    res := win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE),
                    _show_message_box(True, res),
                )
            ],
            [
                QPushButton('恢复窗口显示状态'),
                lambda pid, hwnd: (
                    res := win32gui.ShowWindow(hwnd, win32con.SW_RESTORE),
                   _show_message_box(True, res),
                )
            ],
            [
                QPushButton('隐藏/显示'),
                lambda pid, hwnd:(
                    res :=  win32gui.ShowWindow(
                        hwnd,
                        win32con.SW_HIDE if win32gui.IsWindowVisible(hwnd) else win32con.SW_SHOW
                    ),
                    _show_message_box(True, res),
                )
            ],
            [
                QPushButton('(取消)置顶窗口'),
                lambda pid, hwnd: (
                    window_is_on_top := bool(win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST),
                    win32gui.SetWindowPos(
                        hwnd,
                        win32con.HWND_NOTOPMOST if window_is_on_top else win32con.HWND_TOPMOST,
                        0, 0, 0, 0,
                        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                    ),
                    _show_message_box(True, None),
                )
            ],
            [
                QPushButton('运行源文件'),
                lambda pid, hwnd: os.startfile(self.select_obj.exe()) if self.select_obj else log('未选中窗口'),
            ],
            [
                QPushButton('源文件所在位置'),
                lambda pid, hwnd: subprocess.Popen(f'explorer /select, "{self.select_obj.exe()}"') if self.select_obj else log('未选中窗口'),
            ],
            [
                QPushButton('(取消)挂起所选进程'),
                lambda pid, hwnd:
                    (
                        resume_process(pid),
                        _set_attribute(self.select_process_info, 'suspend', False),
                        log(f"已恢复进程 PID: {pid}")
                    ) if self.select_process_info['suspend']
                    else (
                        suspend_process(pid),
                        _set_attribute(self.select_process_info, 'suspend', True),
                        log(f"已挂起进程 PID: {pid}")
                    ),
            ],
            [
                QPushButton('运行外部程序'),
                lambda: (
                    res := ShowRunDialog(self.winId(), None, None, "运行", "子逸 将根据你所输入的名称，为你打开相应的程序、文件夹、文档或 Internet 资源。", 0),
                    MessageBox(parent=self, title="错误", top_info="无法定位函数 RunFileDlg_win32 于动态链接库 shell32.dll 中", info="", icon=QMessageBox.Critical) if not res and profile_obj['set_up']['show_error_box'] else None
                ),
                {'need': {'pid': False, 'hwnd': False}}
            ]
        ]
        if not is_admin():
            dos_buttons.append([
                QPushButton('获取管理员权限'),
                lambda: run_again_as_admin(self),
                {'need': {'pid': False, 'hwnd': False}}
            ])
        # 将 窗口操作控件 添加至 窗口操作布局
        for index, item in enumerate(dos_buttons):
            def make_slot(func, item) -> Callable[[], Any] | Callable[[], None]:
                '''生成槽函数'''
                def res_func() -> Any | None:
                    '''槽函数'''
                    # 定义辅助函数，检查 pid 和 hwnd 是否有效，并在无效时提示
                    check_pid_and_solve = lambda pid: (
                        True if self.IsProcess(pid)
                        else profile_obj['set_up']['show_warning_box'] and MessageBox(parent=self, title='操作失败', top_info=f'未选中有效进程', info=f"选中的进程无效\n(PID: {pid})", icon=QMessageBox.Warning) and False # 返回 False 以不执行槽函数，下同
                    )
                    check_hwnd_and_solve = lambda hwnd: (
                        True if self.IsWindow(hwnd)
                        else profile_obj['set_up']['show_warning_box'] and MessageBox(parent=self, title='操作失败', top_info=f'未选中有效窗口', info=f"选中的窗口无效\n(句柄: {hwnd})", icon=QMessageBox.Warning) and False
                    )
                    try:
                        # 检查是否选中窗口（检查 pid 和 hwnd 是否有效）
                        if len(item) == 3:
                            # 有自定义配置，检查并传递需要的参数
                            if item[2]['need']['pid'] and item[2]['need']['hwnd']: # type: ignore
                                # 需要 pid 与 hwnd
                                if not check_pid_and_solve(self.select_pid):
                                    return None
                                if not check_hwnd_and_solve(self.select_hwnd):
                                    return None
                                return func(self.select_pid, self.select_hwnd)
                            elif item[2]['need']['pid']: # type: ignore
                                # 需要 pid
                                if not check_pid_and_solve(self.select_pid):
                                    return None
                                return func(self.select_pid)
                            elif item[2]['need']['hwnd']: # type: ignore
                                # 需要 hwnd
                                if not check_hwnd_and_solve(self.select_hwnd):
                                    return None
                                return func(self.select_hwnd)
                            else:
                                return func()
                        elif len(item) == 2:
                            if not check_pid_and_solve(self.select_pid):
                                return None
                            if not check_hwnd_and_solve(self.select_hwnd):
                                return None
                            # 无自定义配置，检查并传递参数
                            return func(self.select_pid, self.select_hwnd)
                        else:
                            raise TypeError(f"处理 {item} 时发生错误：给定的列表长度为 {len(item)} 应为 2 或 3")
                    except Exception:
                        log.error("处理槽函数时发生错误：", traceback.format_exc())
                        return None
                return res_func
            item[0].clicked.connect(make_slot(item[1], item)) # type: ignore
            dos_button_layout.addWidget(item[0], index // max_len_for_1_line, index % max_len_for_1_line)

        # 将 窗口操作布局 添加至 主布局
        main_layout.addLayout(dos_button_layout)

        # 创建 超级布局 并将主布局添加至 超级布局
        self.super_layout = QVBoxLayout()
        self.super_layout.addLayout(main_layout)
        self.setLayout(self.super_layout)

        # 创建 其他按钮布局
        self.other_button_layout = QHBoxLayout()
        # 添加 设置按钮 至 其他按钮布局
        setbutton = QPushButton('设置')
        setbutton.clicked.connect(self.slot_of_setbutton)
        setbutton.setIcon(QIcon(get_file_path("data\\icon\\set_up.png")))
        self.other_button_layout.addWidget(setbutton)
        # 添加 关于按钮 至 其他按钮布局
        about_button = QPushButton('关于')
        about_button.clicked.connect(self.slot_of_about_button)
        about_button.setIcon(QIcon(get_file_path('data\\icon\\about.png')))
        self.other_button_layout.addWidget(about_button)
        # 添加 伸缩空间 至 其他按钮布局，以使按钮左对齐
        self.other_button_layout.addStretch()
        # 将 其他按钮布局 添加至 超级布局
        self.super_layout.addLayout(self.other_button_layout)

        # 设置 超级布局 为 窗口布局
        self.setLayout(self.super_layout)

        # 启动更新窗口计时器
        self.update_window_timer.start(100)
        # 启动更新属性状态计时器
        self.stop_and_start_timer('on_top', 'on_top_time')
        self.stop_and_start_timer('keep_work', 'keep_work_time')
        # 绑定配置文件回调函数
        profile_obj.register_callback(self.slot_of_profile_callback)

    def set_window_border(self, hwnd, borderless: bool | None = None) -> None:
        '''设置窗口为无边框或恢复边框，设置 borderless 为 None 以切换状态'''
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        has_border = style & (win32con.WS_CAPTION | win32con.WS_THICKFRAME)
        if borderless or (borderless is None and has_border):
            # 移除边框和标题栏
            style &= ~win32con.WS_CAPTION
            style &= ~win32con.WS_THICKFRAME
        else:
            # 恢复边框和标题栏
            style |= win32con.WS_CAPTION
            style |= win32con.WS_THICKFRAME
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        # 移动窗口并还原以触发窗口刷新
        left, top, _, _, width, height = self.get_pos(hwnd)
        win32gui.SetWindowPos(
            hwnd, None, left+1, top+1, width+1, height+1,
            0
        )
        win32gui.SetWindowPos(
            hwnd, None, left, top, width, height,
            0
        )

    def record_window_info(self, hwnd: int):
        '''记录窗口信息至配置文件'''
        # log.debug(f'窗口句柄：{hwnd}, {self.IsWindow(hwnd)}')
        if not self.IsWindow(hwnd):
            # log.debug(f'无效的窗口句柄：{hwnd}')
            return
        # 更新配置文件
        try:
            infos = profile_obj['select_window_info']  # 获取所有记录的窗口信息
            set_item = {}  # 目标项
            for item in infos:
                # 枚举，检查当前窗口是否已记录
                if item['id']['class_name'] == win32gui.GetClassName(hwnd) or item['id']['title'] == win32gui.GetWindowText(hwnd):
                    # log.debug(f'已记录的窗口：{item["id"]["class_name"]} - {item["id"]["title"]}')
                    set_item = item
                    break
            else:
                # log.debug(f'未记录的窗口：{win32gui.GetClassName(hwnd)} - {win32gui.GetWindowText(hwnd)}')
                # 无记录，添加记录
                infos.append({})
                set_item = infos[-1]
            # 更新记录
            set_item['id'] = dict()
            set_item['id']['class_name'] = win32gui.GetClassName(hwnd)
            set_item['id']['title'] = win32gui.GetWindowText(hwnd)
            left, top, _, _, width, height = get_window_pos_and_size(hwnd)
            set_item['pos'] = [left, top]
            set_item['size'] = [width, height]
            has_border = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE) & (win32con.WS_CAPTION | win32con.WS_THICKFRAME)
            set_item['has_frame'] = bool(has_border)
            set_item['display_state'] = win32gui.GetWindowPlacement(hwnd)[1]
            set_item['show'] = bool(win32gui.IsWindowVisible(hwnd))
            set_item['is_top'] = bool(win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST)
            # 写入配置文件
            profile_obj.set('select_window_info', infos)
        except:
            log.error(f'更新窗口信息时发生错误:\n{traceback.format_exc()}')

    def use_window_info(self, hwnd: int) -> None:
        '''应用窗口信息'''
        try:
            # 获取窗口信息
            infos = profile_obj['select_window_info']  # 获取所有记录的窗口信息
            for item in infos:
                log.debug(f'枚举窗口信息：{item}')
                # 枚举，检查当前窗口是否已记录
                if item['id']['class_name'] == win32gui.GetClassName(hwnd) or item['id']['title'] == win32gui.GetWindowText(hwnd):
                    log.debug(f'应用已记录的窗口信息：{item["id"]["class_name"]} - {item["id"]["title"]}')
                    # 更新窗口信息
                    if item['display_state'] != 2:
                        # 不为最小化，设置位置
                        win32gui.SetWindowPos(
                            hwnd, None, item['pos'][0], item['pos'][1], item['size'][0], item['size'][1],
                            win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED
                        )
                    # 设置边框
                    self.set_window_border(hwnd, not item['has_frame'])
                    # 设置显示状态
                    win32gui.ShowWindow(hwnd, item['display_state'])
                    # 设置置顶状态
                    win32gui.SetWindowPos(
                        hwnd, win32con.HWND_TOPMOST if item['is_top'] else win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED
                    )
                    # 设置显示状态
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW if item['show'] else win32con.SW_HIDE)
                    break
            else:
                log.debug(f'窗口无历史记录：{win32gui.GetClassName(hwnd)} - {win32gui.GetWindowText(hwnd)}')
                # 无记录，不做更改
        except:
            log.error(f'应用窗口信息时发生错误:\n{traceback.format_exc()}')

    def chose_window(self) -> None:
        '''已选择窗口'''
        log.debug('已选择窗口')
        # 判断句柄是否有效
        if not self.IsWindow(self.select_hwnd):
            log(f'当前句柄“{self.select_hwnd}”无效')
            return
        # 停止选择
        self.stop_get_info()
        self.init_overlay_attribute()
        # 输出状态
        chose_window_hwnd = self.select_hwnd
        log(f"选中窗口句柄为：{chose_window_hwnd}")
        # 正常显示
        self.showNormal()
        # 判断是否需要提权
        log.debug(f"尝试访问进程 PID: {self.select_pid}")
        phandle = ctypes.windll.kernel32.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, self.select_pid)
        if not phandle:
            # 无法访问目标进程
            log.warning(f"无法访问目标窗口，可能是权限不足或进程已结束")
            if MessageBox(parent=self, title='拒绝访问', top_info=f'无法访问进程 PID: {self.select_pid}，是否提权？', icon=QMessageBox.Critical, buttons=('是', '否')) == '是':
                run_again_as_admin(self, f'--hwnd={self.select_hwnd}')
        else:
            ctypes.windll.kernel32.CloseHandle(phandle) # 关闭句柄
        log.debug(f'访问结束')
        # 应用记录的窗口信息
        self.use_window_info(self.select_hwnd) # type: ignore
        # 记录窗口信息
        self.record_window_info(self.select_hwnd) # type: ignore
        log.debug('窗口信息已记录')
        # 更新数据
        self.select_obj = psutil.Process(self.select_pid)
        self.select_process_info['suspend'] = False
        # 监测目标窗口尺寸/位置/标题变化
        self.observe_obj = ObserveWindow(self.select_hwnd, # type: ignore
            lambda old_info, new_info: (
                # 更新输入框文本
                self.sel_wind_info_widgets['window_title']['obj'][0].setText(new_info['title']),
                self.sel_wind_info_widgets['window_pos']['obj'][1].setText(str(new_info['pos'][0])),
                self.sel_wind_info_widgets['window_pos']['obj'][3].setText(str(new_info['pos'][1])),
                self.sel_wind_info_widgets['window_size']['obj'][1].setText(str(new_info['size'][0])),
                self.sel_wind_info_widgets['window_size']['obj'][3].setText(str(new_info['size'][1])),
            ),
            wait_time=0.1
        )
        self.observe_obj.start()
        log.debug('已启动窗口监测器')
        # 更改显示信息
        self.update_input_box()

    def slot_of_profile_callback(self, op_type: OperationType, data: OperationData):
        '''配置文件回调函数'''
        if op_type == OperationType.SET_ITEM and data['key'] == 'set_up':
            # 设置键值对，检查是否更新计时器
            if isinstance(data['new_value'].get('on_top_time', None), (float, int)):
                self.stop_and_start_timer('on_top', 'on_top_time')
            if isinstance(data['new_value'].get('keep_work_time', None), (float, int)):
                self.stop_and_start_timer('keep_work', 'keep_work_time')
            self.change_tray_icon_visible(data)
            self.re_register_start_choose_window_hotkey('+'.join(data['old_value']['start_choose_window_hotkey']))
        elif op_type == OperationType.SET_ALL and data['key'] == 'set_up':
            self.stop_and_start_timer('on_top', 'on_top_time')
            self.stop_and_start_timer('keep_work', 'keep_work_time')
            self.change_tray_icon_visible(data)
            self.re_register_start_choose_window_hotkey('+'.join(data['old_value']['start_choose_window_hotkey']))
        else:
            ...

    def re_register_start_choose_window_hotkey(self, old_hotkey: str | None):
        '''重新注册开始选择窗口热键'''
        if old_hotkey is not None:
            keyboard.remove_hotkey(
                old_hotkey,
            )
        hotkey = '+'.join(profile_obj['set_up']['start_choose_window_hotkey'])
        keyboard.add_hotkey(
            hotkey,
            lambda: self.hotkey_triggered.emit() if not self.is_getting_info else None
        )

    def change_tray_icon_visible(self, data: OperationData) -> None:
        '''检查并切换托盘图标可见状态'''
        if isinstance(data['new_value'].get('show_tray_icon', None), bool):
            # 切换可见状态
            if data['new_value']['show_tray_icon']:
                tray_icon.show()
            else:
                tray_icon.hide()

    def stop_and_start_timer(self, timer_name: str, profile_key: str, root_key: str = 'set_up', default_value: int = -1) -> None:
        '''停止并按配置文件中的时间重新启动计时器'''
        if self.update_window_attribute_timers.get(timer_name, None) is None:
            raise KeyError(f"计时器 {timer_name} 不存在")
        self.update_window_attribute_timers[timer_name].stop()
        time = int(profile_obj.get(root_key, {profile_key: default_value}, using_callback = False).get(profile_key, default_value) * 1000)
        if time >= 0:
            self.update_window_attribute_timers[timer_name].start(time)

    def slot_of_setbutton(self):
        '''设置按钮槽函数'''
        # 创建设置窗口
        self.set_window = SetUpWindow(self)
        # 绑定信号至槽函数
        self.set_window.signal_save.connect(self.slot_of_set_up_window_save_signal)
        # 显示设置窗口
        self.set_window.exec_()
    
    def slot_of_set_up_window_save_signal(self, data: dict) -> None:
        '''设置窗口关闭信号槽函数'''
        # 由于传递信号时对话框已被关闭，故无需再次关闭
        if data['save']:
            profile_obj['set_up'] = data['data']  # 保存更改
        else:
            # 不保存更改
            pass
    
    def slot_of_about_button(self):
        '''关于按钮槽函数'''
        self.about_window = AboutWindow(self)
        self.about_window.exec_()

    def slot_of_update_on_top(self):
        '''更新置顶状态'''
        if profile_obj.get('set_up', {'on_top_time': -1}).get('on_top_time', -1) >= 0:
            # 置顶
            win32gui.SetWindowPos(
                self.winId(), # 目标窗口 # type: ignore
                win32con.HWND_TOPMOST, # 置顶的方式
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE  # 置顶时，不移动，不改变大小，不激活窗口（不获取焦点）
            )

    def slot_of_update_keep_work(self):
        '''更新保持工作状态'''
        if profile_obj.get('set_up', {'keep_work_time': -1}).get('keep_work_time', -1) >= 0:
            # 保持工作
            self.show()
            self.showNormal()

    def slot_of_update_window(self):
        '''更新窗口 / 信息'''
        # 重绘窗口，防止恶意软件的特效覆盖
        self.update()
        # 更新输入框
        is_enable = self.IsWindow(self.select_hwnd) and not self.is_getting_info

        self.sel_wind_info_widgets['window_title']['obj'][0].setEnabled(is_enable)

        self.sel_wind_info_widgets['window_pos']['obj'][1].setEnabled(is_enable)
        self.sel_wind_info_widgets['window_pos']['obj'][3].setEnabled(is_enable)

        self.sel_wind_info_widgets['window_size']['obj'][1].setEnabled(is_enable)
        self.sel_wind_info_widgets['window_size']['obj'][3].setEnabled(is_enable)

        # 更新选中窗口信息至文件
        if not self.is_getting_info:
            self.record_window_info(self.select_hwnd) # type: ignore

    def slot_of_size_title_pos_input_box_edit_finished(self) -> None:
        '''大小/位置/标题输入框 改变槽函数'''
        # 设置窗口属性
        if self.IsWindow(self.select_hwnd) and not any(self.is_setting_input_box[k] for k in self.is_setting_input_box if k in ('pos', 'size')):
            # 选中窗口有效 且 位置/尺寸 输入框由用户改变
            # 编译正则表达式，匹配整数
            match_int = re.compile(r'^-?\d+$')
            # 设置属性
            win32gui.SetWindowPos(  # 设置窗口位置与尺寸
                self.select_hwnd,  # 目标窗口 # type: ignore
                None,  # 置顶状态不变
                # 设置窗口位置
                int(
                    self.sel_wind_info_widgets['window_pos']['obj'][1].text()
                ) if match_int.match(
                    self.sel_wind_info_widgets['window_pos']['obj'][1].text()
                ) else 0,
                int(
                    self.sel_wind_info_widgets['window_pos']['obj'][3].text()
                ) if match_int.match(
                    self.sel_wind_info_widgets['window_pos']['obj'][3].text()
                ) else 0,
                # 设置窗口尺寸
                int(
                    self.sel_wind_info_widgets['window_size']['obj'][1].text()
                ) if match_int.match(
                    self.sel_wind_info_widgets['window_size']['obj'][1].text()
                ) else 0,
                int(
                    self.sel_wind_info_widgets['window_size']['obj'][3].text()
                ) if match_int.match(
                    self.sel_wind_info_widgets['window_size']['obj'][3].text()
                ) else 0,
                win32con.SWP_SHOWWINDOW   # 标志，用于更改窗口显示状态
            )
            win32gui.SetWindowText(self.select_hwnd, self.sel_wind_info_widgets['window_title']['obj'][0].text())  # 设置标题  # type: ignore
            # 设置后更新输入框，确保数据一致
            self.update_input_box()
    
    def update_input_box(self):
        '''更新输入框'''
        left, top, right, bottom, width, height = self.get_pos(self.select_hwnd)
        title = win32gui.GetWindowText(self.select_hwnd) # type: ignore
        exe_file_path = self.select_obj.exe() # type: ignore
        self.sel_wind_info_widgets['window_title']['obj'][0].setText(title)
        self.sel_wind_info_widgets['window_title']['obj'][0].setEnabled(True)

        # 防止exe路径过长撑大窗口
        max_show_len = 49
        filepath_text = exe_file_path if len(exe_file_path) <= max_show_len else exe_file_path[:max_show_len] + '...'

        self.sel_wind_info_widgets['window_exe']['obj'].setText(filepath_text)

        self.sel_wind_info_widgets['window_pos']['obj'][1].setText(str(left))
        self.sel_wind_info_widgets['window_pos']['obj'][1].setEnabled(True)
        self.sel_wind_info_widgets['window_pos']['obj'][3].setText(str(top))
        self.sel_wind_info_widgets['window_pos']['obj'][3].setEnabled(True)

        self.sel_wind_info_widgets['window_size']['obj'][1].setText(str(width))
        self.sel_wind_info_widgets['window_size']['obj'][1].setEnabled(True)
        self.sel_wind_info_widgets['window_size']['obj'][3].setText(str(height))
        self.sel_wind_info_widgets['window_size']['obj'][3].setEnabled(True)

        self.sel_wind_info_widgets['process_pid']['obj'].setText(str(self.select_pid))
        self.sel_wind_info_widgets['process_hwnd']['obj'].setText(str(self.select_hwnd))
    
    def slot_of_start_get_window_button_from_list(self):
        '''从列表中选择窗口'''
        log.debug('开始从窗口列表中获取窗口信息')
        if self.is_getting_info:
            ...
        else:
            log.debug('显示窗口列表选择窗口')
            self.choos_window_list_window = ChooseWindowList(self)
            self.choos_window_list_window.signal_hwnd.connect(self.slot_of_selected_window_from_list)
            self.choos_window_list_window.exec_()

    def slot_of_selected_window_from_list(self, hwnd) -> None:
        '''用户已从列表中选择窗口槽函数'''
        log.log(f'用户已从列表中选择窗口 HWND: {hwnd}')
        # 检查窗口是否有效
        if hwnd <= 0:
            return
        self.select_hwnd = hwnd
        self.select_pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        try:
            self.select_obj = psutil.Process(self.select_pid)
        except (ValueError, psutil.NoSuchProcess):
            log.log(f'PID无效({self.select_pid})')
        else:
            self.update_input_box()
        # 设置按钮状态
        self.start_get_window_button.setEnabled(True)

    def slot_of_start_get_window_button(self):
        '''开始获取窗口信息'''
        log.debug('开始获取窗口信息')
        if self.is_getting_info:
            self.stop_get_info()
            self.init_overlay_attribute()
            self.start_get_window_button.setText("开始获取")
            self.is_getting_info = False
            self.start_get_window_button_from_list.setEnabled(True)
        else:
            self.update_sele_wind_timer.start(50)
            self.start_get_window_button.setText("停止获取")
            self.showMinimized()
            self.is_getting_info = True
            self.start_get_window_button_from_list.setEnabled(False)

    def get_pos(self, hwnd):
        '''获取窗口位置和尺寸信息 返回值格式：left, top, right, bottom, width, height'''
        return get_window_pos_and_size(hwnd)

    def slot_of_update_selected_window_info(self):
        try:
            self._slot_of_update_selected_window_info()
        except pywintypes.error as e:
            # 捕获 pywintypes.error 异常，该异常可能由于 非原子操作的判断 导致 判断结束时窗口已被销毁
            if e.winerror == 87:
                log("发生已知错误：窗口已被销毁或无效")
            elif e.winerror == 1400:
                log("发生已知错误：无效的窗口句柄")
            else:
                log.error(f"更新窗口属性时发生错误：{traceback.format_exc()}")
            self.init_overlay_attribute()
            self.select_pid, self.select_hwnd = None, None
            if self.TOW_obj:
                self.TOW_obj.hide()


    def _slot_of_update_selected_window_info(self) -> None:
        '''更新选中窗口信息'''
        if keyboard.is_pressed('ctrl+alt+c'):
            self.chose_window()
            return

        # 获取鼠标当前位置的窗口信息
        ignore_hwnds = [  # 排除的窗口句柄
            int(main_window.winId())
        ]
        self.select_pid, self.select_hwnd = get_top_window_under_mouse(ignore_hwnds)
        
        # 边界判断
        if not self.IsWindow(self.select_hwnd):
            # 若句柄无效，则重置数据
            self.init_overlay_attribute()
            return
        
        # 若 当前被覆盖窗口 为 新选择的窗口，则获取其位置信息
        left, top, _, _, width, height = self.get_pos(self.select_hwnd)

        self.last_hwnd = self.select_hwnd
        self.last_window_is_top = bool(win32gui.GetWindowLong(self.select_hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST)

        # 若蒙版窗口存在，则 更改蒙版窗口位置和大小 并 返回
        if self.TOW_obj:
            self.TOW_obj.show()
            self.TOW_obj.set_size_and_pos(left, top, width, height)
            return

        # 若蒙版窗口不存在，则 创建新蒙版窗口

        def callback(class_obj: TOW) -> str:
            # 边界判断
            if not self.IsWindow(self.select_hwnd):
                return f"无效的句柄“{self.select_hwnd}”"
            # 获取窗口位置和大小信息
            left, top, _, _, width, height = self.get_pos(self.select_hwnd)
            # 获取窗口其他信息
            title = win32gui.GetWindowText(self.select_hwnd) # type: ignore
            exe_path = psutil.Process(self.select_pid).exe()
            max_show_len = (width-65)//15
            # 更新位置
            class_obj.setGeometry(left, top, width, height)
            return f"""\
            窗口标题：{title}
            文件位置：{"..." if len(exe_path) > max_show_len else ""}{exe_path[-max_show_len:]}
            PID：{self.select_pid}
            窗口句柄：{self.select_hwnd}
            使用[ctrl+alt+c]选择此窗口\
            """.replace("            \n", "\n")

        self.TOW_obj = TOW(left, top, width, height, callback=callback)
        self.TOW_obj.show()

    def stop_get_info(self) -> None:
        '''停止获取窗口信息'''
        self.update_sele_wind_timer.stop()
        self.pause_get_info()

    def pause_get_info(self) -> None:
        '''暂停获取窗口信息'''
        self.is_getting_info = False
        self.start_get_window_button.setText("开始获取")
        self.start_get_window_button_from_list.setEnabled(True)
        if self.TOW_obj:
            self.TOW_obj.hide()

    def init_overlay_attribute(self) -> None:
        '''初始化蒙版属性'''
        # 创建变量，存储当前窗口hwnd
        self.last_hwnd = None
        # 存储蒙版窗口对象
        self.TOW_obj = None
        # 上一个被覆盖窗口是否置顶
        self.last_window_is_top = False
    
    def closeEvent(self, event: QCloseEvent) -> None:
        '''关闭事件'''
        # 停止获取窗口信息
        self.stop_get_info()
        # 隐藏/关闭窗口
        if profile_obj.get('set_up', {'show_tray_icon': True}).get('show_tray_icon', True):
            # 显示托盘图标时隐藏窗口
            log('主窗口隐藏')
            event.ignore() # 忽略关闭事件
            self.hide()
        else:
            log('主窗口被关闭')



class SetUpWindow(QDialog):
    # 设置信号以关闭窗口
    signal_save = pyqtSignal(dict)
    '''配置是否保存，数据结构如下，其中 data 为更新后的设置项：\n{"save":(bool), "data":{...}}。\n若保存，则 save 为 True；\n若不保存，则 save 为 False，此时 data 为 None'''
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # 自动销毁窗口，防止内存泄漏
        self.setAttribute(Qt.WA_DeleteOnClose) # type: ignore

        # 初始化窗口属性
        self.setWindowTitle("设置")
        self.setWindowIcon(QIcon(get_file_path("data\\icon\\set_up.png")))
        self.setFixedSize(500, 400)
        self.setWindowFlag(Qt.Dialog) # type: ignore

        # 初始化属性
        self.set_up_data:dict = profile_obj.get('set_up')  # 设置项值
        self.clicked_ok = False  # 是否点击过确定按钮

        # 初始化界面
        self.init_ui()

    def init_ui(self) -> None:
        # 创建 主布局 及 设置表单布局
        self.main_layout = QVBoxLayout()
        self.set_up_items_layout = QFormLayout()

        # 将 标题 添加至 主布局
        title = QLabel("更改此应用程序的设置")
        title.setStyleSheet("""
            QLabel {
                color: black;                       /* 黑色文本 */
                font-weight: bold;                  /* 粗体 */
                qproperty-alignment: AlignCenter;   /* 水平与垂直居中 */
                font-size: 20px;                    /* 可选：设置字体大小 */
            }
        """)
        self.main_layout.addWidget(title)

        # 将 提示文本 添加至 主布局
        tip_text = QLabel("小提示: 将数值设置为负值以禁用该项")
        tip_text.setStyleSheet("""
            QLabel {
                color: #F2DB1C;                     /* 文本颜色 */
                qproperty-alignment: AlignCenter;   /* 水平与垂直居中 */
                font-size: 12px;                    /* 字体大小 */
            }
        """)
        self.tip_text: QLabel = tip_text
        self.main_layout.addWidget(tip_text)

        # 添加 强制置顶间隔时间 输入框
        self.on_top_time_input_box = QLineEdit()
        self.on_top_time_input_box.setValidator(QDoubleValidator(-1, 60, 3))
        self.on_top_time_input_box.setText(str(self.set_up_data["on_top_time"]))
        self.on_top_time_input_box.textChanged.connect(self.slot_of_on_top_time_input_box)
        self.set_up_items_layout.addRow(QLabel("强制置顶间隔时间(s)"), self.on_top_time_input_box)

        # 添加 强制前台间隔时间 输入框
        self.keep_work_input_box = QLineEdit()
        self.keep_work_input_box.setValidator(QDoubleValidator(-1, 60, 3))
        self.keep_work_input_box.setText(str(self.set_up_data["keep_work_time"]))
        self.keep_work_input_box.textChanged.connect(self.slot_of_keep_work_input_box)
        self.set_up_items_layout.addRow(QLabel("强制前台间隔时间(s)"), self.keep_work_input_box)

        # 添加 开始选择窗口快捷键 按钮
        self.set_start_choose_hotkey_button = QPushButton()
        self.set_start_choose_hotkey_button.setText('+'.join(self.set_up_data["start_choose_window_hotkey"]))
        self.set_start_choose_hotkey_button.setToolTip('点击此处设置快捷键')
        self.set_start_choose_hotkey_button.setStyleSheet('''
            /* 基础样式 */
            QPushButton {
                background-color: #2196F3;  /* 蓝色背景 */
                color: white;               /* 白色文字 */
                border-radius: 5px;         /* 圆角半径 */
                padding: 5px 30px;          /* 增大内边距 */
                min-height: 5px;            /* 最小高度 */
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #0D47A1;  /* 深蓝色边框 */
            }
            
            /* 鼠标悬停效果 */
            QPushButton:hover {
                background-color: #42A5F5;
                border: 2px solid #1976D2;
            }
            
            /* 按下状态 */
            QPushButton:pressed {
                background-color: #0b7dda;
            }
            
            /* 选中状态（点击后保持） */
            QPushButton:checked {
                color: yellow;            /* 文字变黄色 */
            }
        ''')
        self.set_start_choose_hotkey_button.setCheckable(True)
        self.set_start_choose_hotkey_button.clicked.connect(self.slot_of_set_hotkey_to_start_choose)
        self.set_up_items_layout.addRow(QLabel("开始选择窗口快捷键"), self.set_start_choose_hotkey_button)

        # 添加多选框
        self.check_boxes = {
            'allow_hotkey_start_choose':    ('是否允许使用快捷键开始选择窗口', QCheckBox()),
            "on_top_with_UIAccess":         ('是否使用 UIAccess 超级置顶', QCheckBox(), {'restart': True}),
            "show_info_box":                ('是否显示信息对话框', QCheckBox()),
            "show_warning_box":             ('是否显示警告对话框', QCheckBox()),
            "show_error_box":               ('是否显示错误对话框', QCheckBox()),
            'show_tray_icon':               ('是否显示托盘图标', QCheckBox()),
        }
        self.setting_check_boxes = False
        '''正在设置多选框选中状态'''
        for k, v in self.check_boxes.items():
            v[1].setCheckState(Qt.Checked if self.set_up_data[k] else Qt.Unchecked) # type: ignore
            v[1].stateChanged.connect(functools.partial(self.slot_of_show_message_boxes, k))
            self.set_up_items_layout.addRow(*v[:2])

        # 将 设置表单布局 添加至 主布局
        self.main_layout.addLayout(self.set_up_items_layout)

        # 添加 伸缩控件 保持 确认按钮 在底部
        self.main_layout.addStretch()
        # 添加 确认按钮 至 主布局
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.slot_of_ok_button)
        self.main_layout.addWidget(self.ok_button)

        # 设置窗口布局
        self.setLayout(self.main_layout)
    
    def slot_of_on_top_time_input_box(self) -> None:
        try:
            self.set_up_data['on_top_time'] = float(self.on_top_time_input_box.text())
        except ValueError:
            pass

    def slot_of_keep_work_input_box(self) -> None:
        try:
            self.set_up_data['keep_work_time'] = float(self.keep_work_input_box.text())
        except ValueError:
            pass
    
    def slot_of_set_hotkey_to_start_choose(self):
        '''开始设置热键'''
        def listener_func(event: keyboard.KeyboardEvent):
            '''监听按键事件'''
            if event.event_type == 'down':
                # 按下按键，记录按键
                if event.name not in new_hotkey:
                    new_hotkey.append(event.name)
                    self.set_start_choose_hotkey_button.setText(f'> {'+'.join(new_hotkey)} <')
            elif event.event_type == 'up' and new_hotkey:
                # 抬起按键，结束记录
                self.set_up_data['start_choose_window_hotkey'] = new_hotkey
                self.set_start_choose_hotkey_button.setText('+'.join(new_hotkey))
                self.set_start_choose_hotkey_button.setEnabled(True)
                self.set_start_choose_hotkey_button.setChecked(False)
                keyboard.unhook(listener_func)
            return False  # 返回 False 以阻止事件传播
        # 设置按钮状态
        # 设置焦点
        self.set_start_choose_hotkey_button.setFocus(Qt.FocusReason.MouseFocusReason)
        self.set_start_choose_hotkey_button.setEnabled(False)
        self.set_start_choose_hotkey_button.setText(f'> 请输入新快捷键 <')
        new_hotkey = []
        # 监听按键
        keyboard.hook(listener_func)

    
    def slot_of_show_message_boxes(self, k: str) -> None:
        '''多选框槽函数'''
        if self.setting_check_boxes:
            # 程序正在设置状态，不做处理
            return
        if len(self.check_boxes[k]) == 3:
            # 有自定义配置项
            if self.check_boxes[k][2].get('restart', False):
                # 需重启生效，提示用户
                choose = MessageBox(parent=self, title="提示", top_info=f"该更改将在重启后生效", icon=QMessageBox.Information)
                # choose = MessageBox(parent=self, title="提示", top_info=f"该更改将在重启后生效", info='是否重启？', icon=QMessageBox.Information, buttons=("重启", "取消"))
                '''
                if choose == '重启':
                    # 保存设置并重启
                    self.set_up_data[k] = self.check_boxes[k][1].isChecked()
                    self.save_change()
                    exit_the_app(0, restart=True, restart_args=f'--hwnd="{main_window.select_hwnd}"')
                else:
                    # 还原更改
                    self.setting_check_boxes = True
                    self.check_boxes[k][1].setCheckState(Qt.Unchecked if self.check_boxes[k][1].isChecked() else Qt.Checked) # type: ignore
                    self.setting_check_boxes = False
                    return
                '''

        self.set_up_data[k] = self.check_boxes[k][1].isChecked()

    def slot_of_ok_button(self) -> None:
        '''确认按钮槽函数'''
        self.save_change()
        self.close_window()

    def save_change(self):
        '''保存设置'''
        # 关闭窗口并保存更改
        self.signal_save.emit(
            {
                "save": True,
                "data": self.set_up_data
            }
        )

    def close_window(self):
        '''直接关闭窗口，不触发 closeEvent'''
        # 设置点击过确认按钮为True
        self.clicked_ok = True
        # 关闭窗口
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        # 若未点击过确认按钮，则发送信号，防止重复发送
        if not self.clicked_ok:
            # 关闭窗口并不保存更改
            self.signal_save.emit(
            {
                "save": False,
                "data": None
            }
        )
        # 关闭窗口
        return super().closeEvent(event)



class AboutWindow(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # 设置基本属性
        self.setWindowTitle('关于')
        self.setWindowIcon(QIcon(get_file_path('data\\icon\\about.png')))
        self.initUI()
    
    def initUI(self):
        # 创建 主布局
        self.main_layout = QVBoxLayout()
        # 添加文字
        info = QLabel('该软件由 最帅的子逸 制作，以下为部分官方链接')
        self.main_layout.addWidget(info)
        # 添加按钮布局，容纳按钮
        button_layout = QHBoxLayout()
        # 添加按钮
        buttons = [
            [
                '作者 bilibili 空间',
                lambda: webbrowser.open('https://space.bilibili.com/3546756394518735')
            ],
            [
                '软件 github',
                lambda: webbrowser.open('https://github.com/zuishuai-ziyi/WindowTool')
            ],
            [
                '123网盘下载链接',
                lambda: webbrowser.open('https://www.123865.com/s/iRadvd-DJQ0v')
            ]
        ]
        for button_list in buttons:
            button = QPushButton(button_list[0])
            button.clicked.connect(button_list[1])
            button_layout.addWidget(button)
        # 添加 按钮布局 至 主布局
        self.main_layout.addLayout(button_layout)
        # 设置窗口布局
        self.setLayout(self.main_layout)



class ChooseWindowList(QDialog):
    '''选择窗口列表窗口'''
    signal_hwnd = pyqtSignal(int)
    '''关闭窗口信号。携带选中窗口 HWND；-1 表示未选中窗口'''
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # 自动销毁窗口，防止内存泄漏
        self.setAttribute(Qt.WA_DeleteOnClose) # type: ignore

        # 设置基本属性
        self.setWindowTitle('选择窗口')
        self.setWindowIcon(QIcon(get_file_path('data\\icon\\choose.png')))
        self.resize(800, 500)
        self.initUI()
    
    def initUI(self):
        # 最后选中窗口 HWND
        self.selected_hwnd: int | None = None
        # 关闭窗口时是否不发送信号
        self.close_with_no_emit = False
        # 创建 更新窗口列表 计时器
        self.update_window_list_timer = QTimer(self)
        self.update_window_list_timer.timeout.connect(self.slot_of_update_window_list)
        # 创建 主布局
        self.main_layout = QVBoxLayout()
        # 创建表格控件模型
        self.window_table_model = QStandardItemModel()
        self.window_table_model.setHorizontalHeaderLabels(["窗口句柄", "窗口标题"])
        # 创建表格控件
        self.window_table = QTableView()
        self.window_table.setModel(self.window_table_model)
        self.window_table.clicked.connect(self.slot_of_select_item)
        self.window_table.setEditTriggers(QTableView.NoEditTriggers)  # 只读
        self.window_table.setSelectionBehavior(QTableView.SelectRows)  # 每次选中整行
        self.window_table.setAlternatingRowColors(True)  # 行颜色交替
        self.window_table.setSelectionMode(QTableView.SingleSelection)  # 强制单选行
        if (header := self.window_table.verticalHeader()) is not None:
            header.setVisible(False)  # 隐藏垂直表头
        self.main_layout.addWidget(self.window_table)
        # 添加确定按钮
        self.ok_button = QPushButton('确定')
        self.ok_button.clicked.connect(self.slot_of_ok_button)
        self.main_layout.addWidget(self.ok_button)
        # 设置窗口布局
        self.setLayout(self.main_layout)
        # 开始更新窗口列表
        self.slot_of_update_window_list()  # 初始化
        self.update_window_list_timer.start(100)

    def slot_of_update_window_list(self):
        '''更新窗口列表'''
        # 记录选中项目
        if (selected_model := self.window_table.selectionModel()) is None:
            log.error("尝试更新窗口列表时获取到意外数据: 选择模型 为 None")
            MessageBox(parent=self, title="错误", top_info="尝试更新窗口列表时获取到意外数据:\n表格选择模型 为 None", info="单击“确定”以退出", icon=QMessageBox.Critical)
            exit_the_app(ExitCode.UNKNOWN_ERROR, reason="尝试更新窗口列表时获取到意外数据:\n选择模型 为 None")
        else:
            selected_items = selected_model.selectedRows()
        selected_hwnd = None
        if selected_items:
            # 获取当前选中的窗口句柄
            index = selected_items[0]
            item = self.window_table_model.itemFromIndex(index)
            selected_hwnd = item.data(Qt.UserRole) if item else None # type: ignore
        # 记录滚动条位置
        if (scroll_bar := self.window_table.verticalScrollBar()) is not None:
            scroll_bar_value = scroll_bar.value()
        # 匹配项目的下标
        match_item_index = None
        # 清空表格
        self.window_table_model.removeRows(0, self.window_table_model.rowCount())
        def callback(hwnd, _):
            nonlocal match_item_index
            # 获取标题
            title_obj = QStandardItem(
                title if (title := win32gui.GetWindowText(hwnd)) else ""
            )
            # 获取窗口句柄
            hwnd_obj = QStandardItem(str(hwnd))
            if hwnd == selected_hwnd:
                match_item_index = self.window_table_model.rowCount()
            hwnd_obj.setData(hwnd, Qt.UserRole) # type: ignore
            self.window_table_model.appendRow([
                hwnd_obj,
                title_obj,
            ])
            return True
        win32gui.EnumWindows(callback, None)
        # 恢复选中项目
        if match_item_index is not None:
            self.select_row(match_item_index)
            # 设置 选中句柄 为 选中项目第一列的数据
            self.selected_hwnd = self.window_table_model.index(match_item_index, 0).data(Qt.UserRole)  # type: ignore
        else:
            self.selected_hwnd = None
        # 恢复滚动条位置
        if (scroll_bar := self.window_table.verticalScrollBar()) is not None:
            scroll_bar.setValue(scroll_bar_value)

    def select_row(self, row):
        # 创建选择模型实例
        selection_model = self.window_table.selectionModel()
        if selection_model is None:
            return
        # 清除当前的所有选择
        selection_model.clearSelection()
        # 创建一个索引，指定要选择的行
        index = self.window_table_model.index(row, 0)  # 选择第 row 行的第一列
        # 选择该行
        selection_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows) # type: ignore

    def slot_of_select_item(self, item: QListWidgetItem):
        '''选中项目槽函数'''
        log.debug(f"选中项目: {item}")
        if item is None:
            self.selected_hwnd = None
            return
        self.selected_hwnd = item.data(Qt.UserRole) # type: ignore

    def slot_of_ok_button(self):
        '''确定按钮槽函数'''
        self.signal_hwnd.emit(-1 if (self.selected_hwnd is None) else self.selected_hwnd)
        self.close_with_no_emit = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        '''关闭窗口槽函数'''
        if not self.close_with_no_emit:
            self.signal_hwnd.emit(-1)
        return super().closeEvent(event)



class TrayIcon(QSystemTrayIcon):
    '''托盘图标'''
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # 设置基本属性
        self.setIcon(QIcon(get_file_path('data\\icon\\window.png')))
        self.setToolTip('WindowTool 窗口管理工具')
        # 创建菜单
        self.menu = QMenu(parent)
        # 添加菜单项
        self.menu.addAction('主界面', self.slof_of_main_window)
        self.menu.addAction('退出', self.slot_of_exit)
        # 设置菜单
        self.setContextMenu(self.menu)
        # 设置点击图标显示菜单
        self.activated.connect(self.show_menu)

    def show_menu(self, reason: int) -> None:
        '''点击图标显示菜单'''
        if reason == QSystemTrayIcon.Trigger: # type: ignore
            # 左键单击
            main_window.showNormal()

    def slof_of_main_window(self) -> None:
        '''主界面槽函数'''
        main_window.showNormal()

    def slot_of_exit(self) -> None:
        '''退出槽函数'''
        exit_the_app(ExitCode.SUCCESS, reason='用户使用托盘图标退出')



def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False
    
def run_again_as_admin(parent: QWidget | None = None, args = '') -> bool:
    '''以管理员身份重新运行当前程序 返回 是否成功'''
    # 请求UAC提权
    if getattr(sys, 'frozen', False):
        # 打包环境
        exe_path = sys.executable
        params = args
    else:
        # 非打包环境
        exe_path = sys.executable
        script_path = os.path.abspath(__file__)
        params = f'"{script_path}" {args}'

    if ctypes.windll.shell32.ShellExecuteW(
        None, "runas", exe_path, params, None, 1 # SW_NORMAL
    ) <= 32:
        log.error("提升权限失败!")
        if profile_obj['set_up']['show_error_box']:
            MessageBox(parent=parent, title="错误", top_info="提升权限失败!")
        return True
    else:
        return False

@overload
def exit_the_app(code: Literal[ExitCode.SUCCESS], reason: str = '(未提供原因)') -> NoReturn:
    '''退出程序 | 正常退出'''
    ...
@overload
def exit_the_app(code: Literal[ExitCode.UNKNOWN_ERROR], reason: str = '(未提供错误)') -> NoReturn:
    '''退出程序 | 未知错误'''
    ...
@overload
def exit_the_app(code: Literal[ExitCode.RESTART], reason: str = '(未提供原因)', restart_args: str = '') -> NoReturn:
    '''退出程序 | 重启'''
    ...
@overload
def exit_the_app(code: int, reason: str = '(未提供原因)') -> NoReturn:
    '''退出程序 | 其他原因'''
    ...
def exit_the_app(code: ExitCode | int = ExitCode.SUCCESS, reason: str = '(无原因)', restart_args: str = '') -> NoReturn:
    '''退出程序'''
    # 打印日志
    if isinstance(code, ExitCode):
        match code:
            case ExitCode.SUCCESS:
                log(f'程序正常退出 | 退出原因 {reason}')
            case ExitCode.UNKNOWN_ERROR:
                log.error(f'程序因意外错误退出 | 错误信息如下:\n{reason}')
            case ExitCode.RESTART:
                log(f'程序重启 | 重启原因 {reason} 重启时将提供以下参数 {restart_args}')
                # 重启程序
                if getattr(sys, 'frozen', False):
                    # 打包环境，运行可执行文件
                    executable = sys.executable
                    cmd = f"\"{executable}\" \"{restart_args}\""
                else:
                    # 开发环境，使用解释器执行源代码
                    python = sys.executable
                    script = sys.argv[0]
                    cmd = f"{python} \"{script}\" {restart_args}"
                log(f'即将运行以下命令进行重启: {cmd}')
                subprocess.Popen(cmd)
    else:
        log.info(f'程序因其他原因退出 | 退出代码 {code} 原因 {reason}')

    # 释放资源
    free_resource()

    # 退出程序
    exit_code = code == ExitCode.SUCCESS or code == ExitCode.RESTART
    os._exit(exit_code)

def free_resource() -> None:
    '''释放资源'''
    try:
        if main_window.observe_obj and main_window.observe_obj.is_observing():
            # 停止观察
            main_window.observe_obj.stop()
    except Exception:
        pass

def init() -> argparse.Namespace | None:
    '''初始化'''
    global profile_obj, log, command_line_args
    # 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument('--hwnd', type=str, default=None, help='需选中窗口的句柄')
    command_line_args = parser.parse_args()
    # 验证命令行参数是否有效
    if not(isinstance(command_line_args.hwnd, str) and command_line_args.hwnd.isnumeric()):
        command_line_args.hwnd = None
    if profile_obj['set_up']['on_top_with_UIAccess']:
        if is_admin():
            log('已以管理员身份运行，尝试启用 UIAccess...')
            try:
                # 加载 UIAccess 库
                load_res = load_UIAccess_lib()
                if load_res is None:
                    MessageBox(parent=None, title="错误", top_info="尝试启用 UIAccess 时发生错误，详情请查阅日志", icon=QMessageBox.Critical)
                    return None
                _, IsUIA, StartUIA = load_res
                if not IsUIA():
                    if getattr(sys, 'frozen', False):
                        # 打包环境
                        exe_path = sys.executable
                        params = 'app'
                    else:
                        # 非打包环境
                        exe_path = sys.executable
                        script_path = os.path.abspath(__file__)
                        params = f'pythonw "{script_path}"'
                    if command_line_args.hwnd:
                        params += f' --hwnd={command_line_args.hwnd}'
                    pid = wintypes.DWORD(0)
                    if not StartUIA(exe_path, params, 0, ctypes.byref(pid), get_session_id()):
                        raise ctypes.WinError(ctypes.get_last_error())
                    else:
                        log(f'UIAccess 启动成功，PID: {pid.value}')
                        exit_the_app(ExitCode.SUCCESS, reason='UIAccess 已启动，停止当前进程')
                else:
                    log('UIAccess 已启用')
            except Exception:
                log.warning(f'UIAccess 加载失败:\n{traceback.format_exc()}')
        else:
            log('无管理员权限，无法启用 UIAccess')
            if MessageBox(parent=None, title="提示", top_info="无法启用 UIAccess 置顶：权限不足", info='是否提升权限并启用？', buttons=('提权并启用', '不提权并继续')) == '提权并启用':
                log("尝试提权并重启")
                run_again_as_admin()
            log('不提权并继续')



if __name__ == "__main__":
    try:
        # 初始化程序
        init()
        # 创建应用程序实例
        app = QApplication(sys.argv)
        # 创建主窗口
        main_window = MainWindow()
        # 创建托盘图标
        tray_icon = TrayIcon()
        # 根据命令行参数修改选中窗口
        if command_line_args.hwnd and main_window.IsWindow(select_hwnd := int(command_line_args.hwnd)): # type: ignore
            main_window.select_hwnd = select_hwnd
            main_window.select_pid = win32process.GetWindowThreadProcessId(main_window.select_hwnd)[1]
            main_window.chose_window()
        # 显示窗口
        main_window.show()
        # 显示托盘图标
        if profile_obj['set_up']['show_tray_icon']:
            tray_icon.show()
        # 运行应用程序事件循环
        exit_the_app(app.exec(), reason='应用程序事件循环结束')
    except:
        log.critical(f"发生错误:\n{traceback.format_exc()}")
        if hasattr(sys, 'frozen'):
            # 若为打包结果，则提示
            MessageBox(title='错误', top_info='发生未知错误', info=f'{traceback.format_exc()}', icon=QMessageBox.Critical)
            exit_the_app(ExitCode.UNKNOWN_ERROR, reason=f'打包结果中发生未知错误: \n{traceback.format_exc()}')
        try:
            while 1:
                time.sleep(0.5)
        except KeyboardInterrupt:
            log('程序终止')
            try:
                exit_the_app(1, reason='发生未知错误时，用户使用 ctrl+c 终止程序')
            except Exception:
                log('无法调用 exit_the_app 函数进行终止')
                exit(1)

# 打包命令 建议使用 pack.bat 打包
# pyinstaller main.py --noconsole --add-data "data:data" -i "D:\_ziyi_home_\ziyi_home\文件\code\python\wowo\开发中\windows\data\icon\window.png"

