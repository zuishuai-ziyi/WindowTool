from transparent_overlay_window import TransparentOverlayWindow as TOW
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QFormLayout, QHBoxLayout, QDialog, QLineEdit, QCheckBox, QSizePolicy
from PyQt5.QtGui import QCloseEvent, QIcon, QDoubleValidator, QFontMetrics
from PyQt5.QtCore import QEvent, Qt, QTimer, pyqtSignal
from api import get_top_window_under_mouse, get_window_pos_and_size
from buttonbox import main as show_buttonbox
from kill_process import kill_process
from delete_file import delete_file
from suspend_process import suspend_process, resume_process
from other_window import input_box_window
from operation_profile import ProfileShell as ProfileShellClass
from observe_window import ObserveWindow
from typing import Any, Dict, Literal, List, Callable, NoReturn, Iterable
import sys, win32gui, win32con, win32com.client, psutil, keyboard, ctypes, os, traceback, pywintypes, time, threading, webbrowser, re


class MainWindow(QWidget):
    '''主窗口'''
    def __init__(self) -> None:
        super().__init__()

        # 创建计时器，用于更新选中窗口信息
        self.update_sele_wind_timer = QTimer(self)
        self.update_sele_wind_timer.timeout.connect(self.slot_of_update_selected_window_info)
        # 创建计时器，用于更新窗口
        self.update_window_timer = QTimer(self)
        self.update_window_timer.timeout.connect(self.slot_of_update_window)

        # 初始化蒙版属性
        self.init_overlay_attribute()

        # 设置窗口标志
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint  # type: ignore
        )

        # 设置窗口图标
        self.setWindowIcon(QIcon(get_file_path('data\\icon\\window.png')))

        # 设置窗口标题
        self.setWindowTitle('Windows')

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

        self.IsWindow = lambda hwnd: isinstance(hwnd, int) and win32gui.IsWindow(hwnd)
        self.IsProcess = lambda pid: isinstance(pid, int) and psutil.pid_exists(pid)

        self.main_UI()

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
        self.is_setting_input_box: Dict[str, bool] = dict((item, False) for item in
            {'title', 'pos', 'size'}
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

        # 添加 开始获取窗口 按钮
        self.start_get_window_button = QPushButton("开始获取")
        self.start_get_window_button.clicked.connect(self.slot_of_start_get_window_button)
        main_layout.addWidget(self.start_get_window_button)

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
        max_len_for_1_line = 3  # 单行最大控件数
        dos_buttons: List[List[QPushButton | Callable | Dict[Literal['need'], Dict[Literal['pid'] | Literal['hwnd'], bool]]]] = [
            [
                QPushButton('结束所选进程'),
                lambda pid, hwnd: (
                    kill_process(pid),
                    print(f"已发送终止信号至进程 PID: {pid}")
                )
            ],
            [
                QPushButton('删除所选进程源文件'),
                lambda pid, hwnd: (
                    (
                        kill_process(pid),
                        pid_exe := self.select_obj.exe(),
                        success := delete_file(pid_exe),
                        QMessageBox.information(self, '删除成功', f'文件 {pid_exe} 删除成功') if success else 
                        QMessageBox.critical(self, '删除失败', f'文件 {pid_exe} 删除失败')
                    ) if self.select_obj else QMessageBox.warning(self, '未选中进程', '请先选中进程')
                )
            ],
            [
                QPushButton('窗口无边框化'),
                lambda pid, hwnd: self.set_window_border(hwnd, True),
                {'need': {'pid': True, 'hwnd': True}}
            ],
            [
                QPushButton('窗口边框状态恢复'),
                lambda pid, hwnd: self.set_window_border(hwnd, False),
                {'need': {'pid': True, 'hwnd': True}}
            ],
            [
                QPushButton('窗口最小化'),
                lambda pid, hwnd: win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            ],
            [
                QPushButton('窗口最大化'),
                lambda pid, hwnd: win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            ],
            [
                QPushButton('恢复窗口大小'),
                lambda pid, hwnd: win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            ],
            [
                QPushButton('隐藏/显示'),
                lambda pid, hwnd:
                    win32gui.ShowWindow(
                        hwnd,
                        win32con.SW_HIDE if win32gui.IsWindowVisible(hwnd) else win32con.SW_SHOW
                    )
            ],
            [
                QPushButton('运行源文件'),
                lambda: os.startfile(self.select_obj.exe()) if self.select_obj else print('未选中窗口'),
                {'need': {'pid': False, 'hwnd': False}}
            ],
            [
                QPushButton('(取消)挂起所选进程'),
                lambda pid, hwnd:
                    (
                        resume_process(pid),
                        _set_attribute(self.select_process_info, 'suspend', False),
                        print(f"已恢复进程 PID: {pid}")
                    ) if self.select_process_info['suspend']
                    else (
                        suspend_process(pid),
                        _set_attribute(self.select_process_info, 'suspend', True),
                        print(f"已挂起进程 PID: {pid}")
                    ),
            ],
            [
                QPushButton('运行外部程序'),
                lambda: (
                    win32com.client.Dispatch("Shell.Application").FileRun() # 打开标准“运行”对话框
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
                    check_pid_and_solve = lambda pid: (  # 检查 pid 是否为 None 并在为 None 时报错
                        True if self.IsProcess(pid)
                        else QMessageBox.warning(self, '操作失败', f'未选中进程或进程{pid}无效，请先选中进程') and False # 阻止默认操作
                    )
                    check_hwnd_and_solve = lambda hwnd: (  # 检查 hwnd 是否为 None 并在为 None 时报错
                        True if self.IsWindow(hwnd)
                        else QMessageBox.warning(self, '操作失败', f'未选中窗口或窗口{hwnd}无效，请先选中窗口') and False # 阻止默认操作
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
                        print("发生错误：", traceback.format_exc())
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
        self.update_window_timer.start(0)

    def set_window_border(self, hwnd, borderless: bool = True) -> None:
        '''设置窗口为无边框或恢复边框'''
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        if borderless:
            # 移除边框和标题栏
            style &= ~win32con.WS_CAPTION
            style &= ~win32con.WS_THICKFRAME
        else:
            # 恢复边框和标题栏
            style |= win32con.WS_CAPTION
            style |= win32con.WS_THICKFRAME
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        # 触发窗口刷新
        win32gui.SetWindowPos(
            hwnd, None, 0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED
        )

    def chose_window(self) -> None:
        '''已选择窗口'''
        # 判断句柄是否有效
        if not self.IsWindow(self.select_hwnd):
            print(f'[LOG]   当前句柄“{self.select_hwnd}”无效')
            return
        # 停止选择
        self.stop_get_info()
        self.init_overlay_attribute()
        # 输出状态
        chose_window_hwnd = self.select_hwnd
        print(f"[LOG]   选中窗口句柄为：{chose_window_hwnd}")
        # 正常显示
        self.showNormal()
        # 更新数据
        self.select_obj = psutil.Process(self.select_pid)
        self.select_process_info['suspend'] = False
        # 监测目标窗口尺寸/位置/标题变化
        self.observe_obj = ObserveWindow(self.select_hwnd, # type: ignore
            lambda old_info, new_info: (
                # 更新设置状态，防止更新窗口位置
                # _set_attribute(self.is_setting_input_box, ('title', 'pos', 'size'), True),
                # 更新输入框文本
                self.sel_wind_info_widgets['window_title']['obj'][0].setText(new_info['title']),
                self.sel_wind_info_widgets['window_pos']['obj'][1].setText(str(new_info['pos'][0])),
                self.sel_wind_info_widgets['window_pos']['obj'][3].setText(str(new_info['pos'][1])),
                self.sel_wind_info_widgets['window_size']['obj'][1].setText(str(new_info['size'][0])),
                self.sel_wind_info_widgets['window_size']['obj'][3].setText(str(new_info['size'][1])),
                # 更新文本后重置设置状态
                # _set_attribute(self.is_setting_input_box, ('title', 'pos', 'size'), False),
            ),
            wait_time=0
        )
        self.observe_obj.start()
        # 更改显示信息
        self.update_input_box()

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

    def slot_of_update_window(self):
        '''更新窗口'''
        # 重绘窗口，防止恶意软件的特效覆盖
        self.update()
        # 判断是否强制置顶
        if 0 <= profile_obj.get('set_up', {'on_top_time': 0}).get('on_top_time', 0) <= time.time() - self.last_on_top_time:
            # 重置时间
            self.last_on_top_time = time.time()
            # 置顶
            win32gui.SetWindowPos(
                self.winId(), # 指定窗口 # type: ignore
                win32con.HWND_TOPMOST, # 置顶的方式
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE  # 置顶时，不移动，不改变大小，不激活窗口（不获取焦点）
            )
        if 0 <= profile_obj.get('set_up', {'keep_work_time': 0}).get('keep_work_time', 0) <= time.time() - self.last_keep_work_time:
            # 重置时间
            self.last_keep_work_time = time.time()
            # 恢复状态
            self.showNormal()
        # 更新输入框
        select_is_window = self.IsWindow(self.select_hwnd)

        self.sel_wind_info_widgets['window_title']['obj'][0].setEnabled(select_is_window)

        self.sel_wind_info_widgets['window_pos']['obj'][1].setEnabled(select_is_window)
        self.sel_wind_info_widgets['window_pos']['obj'][3].setEnabled(select_is_window)

        self.sel_wind_info_widgets['window_size']['obj'][1].setEnabled(select_is_window)
        self.sel_wind_info_widgets['window_size']['obj'][3].setEnabled(select_is_window)

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
            win32gui.SetWindowText(self.select_hwnd, self.sel_wind_info_widgets['window_title']['obj'][0].text())  # type: ignore # 设置标题
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
        metrics = QFontMetrics(self.sel_wind_info_widgets['window_exe']['obj'].font())
        max_show_len = 50
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

    def slot_of_start_get_window_button(self):
        '''开始获取窗口信息'''
        if self.is_getting_info:
            self.stop_get_info()
            self.init_overlay_attribute()
            self.start_get_window_button.setText("开始获取")
            self.is_getting_info = False
        else:
            self.update_sele_wind_timer.start(0)
            self.start_get_window_button.setText("停止获取")
            self.showMinimized()
            self.is_getting_info = True

    def get_pos(self, hwnd):
        '''获取窗口位置信息'''
        return get_window_pos_and_size(hwnd)

    def slot_of_update_selected_window_info(self):
        try:
            self._slot_of_update_selected_window_info()
        except pywintypes.error as e:
            # 捕获 pywintypes.error 异常，该异常可能由于 非原子操作的判断 导致 判断结束时窗口已被销毁
            if e.winerror == 87:
                print("发生已知错误：窗口已被销毁或无效")
            elif e.winerror == 1400:
                print("发生已知错误：无效的窗口句柄")
            else:
                print(f"发生错误：{e}")
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
        if self.last_hwnd == self.select_hwnd:
            # 若 当前被覆盖窗口 与 上一次选中窗口 相同，则：
            # 将 当前被覆盖窗口 取消置顶，防止覆盖 蒙版窗口
            win32gui.SetWindowPos(
                self.select_hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | 
                win32con.SWP_NOSIZE
            )
            return
        
        # 若 当前被覆盖窗口 为 新选择的窗口，则获取其位置信息
        left, top, _, _, width, height = self.get_pos(self.select_hwnd)

        # 将上一个被覆盖窗口置顶状态恢复
        if self.IsWindow(self.last_hwnd):
            win32gui.SetWindowPos(
                self.last_hwnd, win32con.HWND_TOPMOST if self.last_window_is_top else win32con.HWND_NOTOPMOST, 0, 0, 0, 0, # type: ignore
                win32con.SWP_NOMOVE |
                win32con.SWP_NOSIZE
            )

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


    def closeEvent(self, event) -> None:
        self.stop_get_info()

    def stop_get_info(self) -> None:
        '''停止获取窗口信息'''
        self.update_sele_wind_timer.stop()
        self.pause_get_info()

    def pause_get_info(self) -> None:
        '''暂停获取窗口信息'''
        self.is_getting_info = False
        self.start_get_window_button.setText("开始获取")
        if self.last_hwnd:
            # 将上一个被覆盖窗口置顶状态恢复
            win32gui.SetWindowPos(
                self.last_hwnd, win32con.HWND_TOPMOST if self.last_window_is_top else win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | 
                win32con.SWP_NOSIZE
            )
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




class SetUpWindow(QDialog):
    # 设置信号以关闭窗口
    signal_save = pyqtSignal(dict)
    '''配置是否保存，数据结构如下，其中 data 为更新后的设置项：\n{"save":(bool), "data":{...}}。\n若保存，则 save 为 True；\n若不保存，则 save 为 False，此时 data 为 None'''
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # 初始化窗口属性
        self.setWindowTitle("设置")
        self.setWindowIcon(QIcon(get_file_path("data\\icon\\set_up.png")))
        self.setFixedSize(400, 300)
        self.setWindowFlag(Qt.Dialog) # type: ignore

        # 初始化属性
        self.set_up_datas:dict = profile_obj.get(  # 设置项值
            'set_up',
            {
                "on_top_time": -1.0, # 强制置顶时间间隔    负数表示不置顶
                "keep_work_time": -1.0 # 强制前台时间间隔  负数表示不强制在前台
            }
        )
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
                color: gray;                        /* 灰色文本 */
                qproperty-alignment: AlignCenter;   /* 水平与垂直居中 */
                font-size: 12px;                    /* 可选：设置字体大小 */
            }
        """)
        self.tip_text: QLabel = tip_text
        self.main_layout.addWidget(tip_text)

        # 添加 强制置顶间隔时间 输入框
        self.on_top_time_input_box = QLineEdit()
        self.on_top_time_input_box.setValidator(QDoubleValidator(-1, 60, 3))
        self.on_top_time_input_box.setText(str(self.set_up_datas["on_top_time"]))
        self.on_top_time_input_box.textChanged.connect(self.slot_of_on_top_time_input_box)
        self.set_up_items_layout.addRow(QLabel("强制置顶间隔时间(s)"), self.on_top_time_input_box)

        # 添加 强制前台间隔时间 输入框
        self.keep_work_input_box = QLineEdit()
        self.keep_work_input_box.setValidator(QDoubleValidator(-1, 60, 3))
        self.keep_work_input_box.setText(str(self.set_up_datas["keep_work_time"]))
        self.keep_work_input_box.textChanged.connect(self.slot_of_keep_work_input_box)
        self.set_up_items_layout.addRow(QLabel("强制前台间隔时间(s)"), self.keep_work_input_box)

        # 添加 窗口允许最小化 复选框
        self.allow_minimize_check_box = QCheckBox("窗口允许最小化")
        self.allow_minimize_check_box.setChecked(self.set_up_datas.get("allow_minimize", False))
        self.allow_minimize_check_box.stateChanged.connect(self.slot_of_allow_minimize_check_box)
        self.set_up_items_layout.addRow(self.allow_minimize_check_box)

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
            self.set_up_datas['on_top_time'] = float(self.on_top_time_input_box.text())
        except ValueError:
            print("[WARN]  用户输入无效")

    def slot_of_keep_work_input_box(self) -> None:
        try:
            self.set_up_datas['keep_work_time'] = float(self.keep_work_input_box.text())
        except ValueError:
            print("[WARN]  用户输入无效")

    def slot_of_allow_minimize_check_box(self) -> None:
        try:
            self.set_up_datas['allow_minimize'] = self.allow_minimize_check_box.isChecked()
        except ValueError:
            print("[WARN]  复选框状态获取失败")

    def slot_of_ok_button(self) -> None:
        '''确认按钮槽函数'''
        # 关闭窗口并保存更改
        self.signal_save.emit(
            {
                "save": True,
                "data": self.set_up_datas
            }
        )
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


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False
    
def run_again_as_admin(parent = None) -> None:
    '''以管理员身份重新运行当前程序'''
    # 请求UAC提权
    if ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, not hasattr(sys, 'frozen') # hasattr(sys, 'frozen') -> 是否在打包后的环境中 此处最后一个参数的值影响提权后命令窗口是否显示，0为不显示 ⚠️当参数为0时，Windows会阻止子窗口渲染，导致所有Qt窗口失效 但不影打包为【单文件】的程序⚠️
    ) <= 32:
        print("[ERROR] 提升权限失败!")
        QMessageBox.critical(parent, "错误", "提升权限失败!")


def get_file_path(file_path: str):
    """获取资源文件实际绝对路径"""
    return os.path.join(sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.abspath("."), file_path) # type: ignore


def exit_the_app(code: int = 0) -> NoReturn:
    '''退出程序'''
    # 释放资源
    if main_window.observe_obj and main_window.observe_obj.is_observing():
        # 停止观察
        main_window.observe_obj.stop()
    os._exit(code)


if __name__ == "__main__":
    try:
        # 读取配置文件
        try:
            profile_obj = ProfileShellClass(get_file_path("data\\profile\\data.yaml"))
        except Exception as e:
            print(f"配置文件加载失败: {e}")
            os._exit(0)
        # 创建应用程序实例
        app = QApplication(sys.argv)
        main_window = MainWindow()
        main_window.show()
        exit_the_app(app.exec())
    except:
        print(traceback.format_exc())
        if hasattr(sys, 'frozen'):
            # 若为打包结果，则忽略异常
            exit_the_app()
        while 1:
            time.sleep(0.5)

# pyinstaller main.py --noconsole --add-data "data:data" -i "D:\_ziyi_home_\ziyi_home\文件\code\python\wowo\开发中\windows\data\icon\window.png"
