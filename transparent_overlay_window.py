import sys, inspect
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush
from typing import Callable, Optional

class TransparentOverlayWindow(QWidget):
    '''透明蒙版'''
    def __init__(self, x, y, width, height, callback:"Callable[[Optional[TransparentOverlayWindow]], str] | None"=None, text_style_sheet:str|None=None, edging_color:None|QColor=None, edging_width:None|int=None, background:None|QColor=None):
        super().__init__()
        self.callback = self.default_callback if callback is None else callback
        self.style_sheet = \
            """\
            color: white;              /* 白色文字 */
            font: bold 16px "Arial";   /* 字体样式 */
            background: transparent;   /* 透明背景 */
            """\
            if text_style_sheet is None else text_style_sheet
        self.edging_color = QColor(255, 255, 255, 255) if edging_color is None else edging_color
        self.background_color = QColor(128, 128, 128, 180) if background is None else background
        self.edging_width = 2 if edging_width is None else edging_width

        # 设置窗口属性：无边框、置顶、透明背景、输入透明
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # type: ignore
            Qt.WindowStaysOnTopHint |  # type: ignore
            Qt.Tool |  # type: ignore
            # Qt.X11BypassWindowManagerHint |  # type: ignore
            Qt.WindowTransparentForInput  # 允许鼠标事件穿透 # type: ignore
        )
        self.setAttribute(Qt.WA_TranslucentBackground)  # type: ignore
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # type: ignore # 确保鼠标事件穿透
        
        # 设置窗口位置和大小
        self.setGeometry(x, y, width, height)

        # 保存尺寸信息用于绘制
        self._width = width
        self._height = height

        # 创建显示标签
        self.label = QLabel(self)
        self.label.setGeometry(0, 0, width, height)
        self.label.setAlignment(Qt.AlignCenter)  # type: ignore
        self.label.setStyleSheet(self.style_sheet)

        # 初始化文字
        self.update_text()
        
        # 设置定时器定期更新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_text)
        self.timer.start(10)  # 更新

    def paintEvent(self, event) -> None:
        """自定义绘制半透明背景和边框"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # 抗锯齿

        # 绘制半透明灰色背景 (RGBA: 128,128,128,180 - 70%不透明)
        painter.setBrush(QBrush(self.background_color))
        painter.setPen(Qt.NoPen)  # type: ignore
        painter.drawRoundedRect(2, 2, self._width-4, self._height-4, 5, 5)
        
        # 绘制白色边框
        painter.setBrush(Qt.NoBrush)  # type: ignore
        painter.setPen(QPen(self.edging_color, self.edging_width))  # 白色，完全不透明
        painter.drawRoundedRect(0, 0, self._width, self._height, 5, 5)
    
    def event(self, event: QEvent) -> bool:
        """重写事件处理，确保所有鼠标事件被忽略"""
        if event.type() in (
            QEvent.MouseButtonPress,  # type: ignore
            QEvent.MouseButtonRelease,  # type: ignore
            QEvent.MouseMove,  # type: ignore
            QEvent.HoverMove,  # type: ignore
            QEvent.HoverEnter,  # type: ignore
            QEvent.HoverLeave,  # type: ignore
            QEvent.Enter,  # type: ignore
            QEvent.Leave  # type: ignore
        ):
            # 忽略所有鼠标相关事件
            return False
        return super().event(event)
    
    def set_size_and_pos(self, x: int, y: int, width: int, height: int) -> None:
        """设置窗口位置及大小"""
        self._width = width
        self._height = height
        self.setGeometry(x, y, width, height)
        self.label.setGeometry(0, 0, width, height)
        self.update()

    # 回调函数
    def default_callback(self) -> str:
        return "默认文本"

    # 更新显示文字
    def update_text(self) -> None:
        # 获取函数所需参数
        parameter_count = len(inspect.signature(self.callback).parameters)
        # 定义全部参数
        parameters = (self,)
        # 目前传递的参数
        now_parameters = parameters[:parameter_count]  # 裁切区间：[)
        # 解包参数并传递
        self.label.setText(self.callback(*now_parameters))

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置显示位置和大小
    width, height = 300, 120

    # 计算位置 (右上角)
    x = 0
    y = 0

    # 创建并显示窗口
    window = TransparentOverlayWindow(x, y, width, height)
    window.show()
    
    # 添加ESC键关闭功能
    from PyQt5.QtWidgets import QShortcut
    from PyQt5.QtGui import QKeySequence
    QShortcut(QKeySequence("Esc"), window).activated.connect(sys.exit)

    app.exec_()