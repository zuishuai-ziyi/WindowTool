from transparent_overlay_window import TransparentOverlayWindow as TOW
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QFormLayout, QHBoxLayout, QDialog, QLineEdit
from PyQt5.QtGui import QCloseEvent, QIcon, QDoubleValidator, QRegExpValidator, QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRegExp
from operation_profile import profile_shell as ProfileShellClass
from typing import Any, Dict, Literal, List, Callable, Never
import sys, win32gui, win32con, psutil, keyboard, ctypes, os, traceback, pywintypes, time, pyautogui, functools

class input_box_window(QDialog):
    def __init__(self, parent: None | QWidget = None, window_pos: tuple | None = None, window_size: tuple = (300, 100), title: str='', icon_path: str | None=None, info_text: str = '请输入数据', buttons: None | list | tuple = None, input_box_default_text: str = '', input_box_tip: str = '', input_text_chang_callback: None | Callable[['input_box_window', 'QLineEdit'], Any] = None, button_click_callback: None | Callable[['input_box_window', 'QPushButton', 'QLineEdit'], Any] = None, close_window_callback: None | Callable[['input_box_window', 'QLineEdit'], Any] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        # 设置图标
        self.setWindowIcon(QIcon() if icon_path is None else QIcon(icon_path))
        middle_pos = (pyautogui.size()[0] // 2 - window_size[0] // 2 , pyautogui.size()[1] // 2 - window_size[1] // 2)
        self.setGeometry(*(middle_pos if window_pos is None else window_size), *window_size)
        # 设置属性
        self.input_text_chang_callback: Callable[['input_box_window', 'QLineEdit'], Any] = \
            (lambda window, obj: print(obj.text())) \
            if input_text_chang_callback is None else input_text_chang_callback
        self.button_click_callback: Callable[['input_box_window', 'QPushButton', 'QLineEdit'], Any] = \
            (lambda window, button_obj, input_box_obj: (window.close(), print(f"选择按钮文本：{button_obj.text()} || 输入框文本: {input_box_obj.text()}"))) \
            if button_click_callback is None else button_click_callback
        self.close_window_callback: Callable[['input_box_window', 'QLineEdit'], Any] = \
            (lambda window, input_box_obj: print(f'窗口关闭 | 输入框文本: {input_box_obj.text()}')) \
            if close_window_callback is None else close_window_callback
        # 初始化界面
        self.initUI(['确定'] if buttons is None else buttons, input_box_default_text, input_box_tip, info_text)

    def initUI(self, buttons: list | tuple, input_box_default_text: str, input_box_tip: str, info_text: str) -> None:
        # 创建总布局
        self.main_layout = QVBoxLayout()
        # 添加信息文本
        self.main_layout.addWidget(QLabel(info_text))
        # 添加输入框
        self.input_box = QLineEdit(input_box_default_text)
        self.input_box.setPlaceholderText(input_box_tip)
        self.input_box.textChanged.connect(functools.partial(self.solt_of_input_box))
        # 将 输入框 添加至 主布局
        self.main_layout.addWidget(self.input_box)
        # 添加弹簧
        self.main_layout.addStretch()
        # 创建按钮布局并添加按钮
        self.buttons_layout = QHBoxLayout()
        for button in buttons:
            button_obj = QPushButton(button)
            # 绑定槽函数
            button_obj.clicked.connect(functools.partial(self.solt_of_buttons, button_obj))
            self.buttons_layout.addWidget(button_obj)
        # 将 按钮布局 添加至 主布局
        self.main_layout.addLayout(self.buttons_layout)
        # 设置窗口布局
        self.setLayout(self.main_layout)

    def solt_of_buttons(self, button_obj: QPushButton) -> None:
        print('点击', button_obj.text(), self.input_box.text(), id(self.button_click_callback))
        self.button_click_callback(self, button_obj, self.input_box)
    
    def solt_of_input_box(self):
        self.input_text_chang_callback(self, self.input_box)

    def closeEvent(self, a0: QCloseEvent) -> None:
        self.close_window_callback(self, self.input_box)
        return super().closeEvent(a0)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = input_box_window(input_box_tip='请输入文本', buttons=('确定', '取消'), input_box_default_text='默认文本', title='标题')
    window.show()
    window.exec()
    # a = lambda window, button, input_box: (print('cl ', input_box.text()))
    # print(id(a))
    # input_box_window(
    #     title='运行',
    #     info_text='子逸 将根据你所输入的名称，为你打开相应的程序、文件夹、文档或 Internet 资源。',
    #     buttons=('确定', '取消'),
    #     input_box_tip='请在此处输入...',
    #     button_click_callback = a,
    # ).exec_()
    app.exec()
