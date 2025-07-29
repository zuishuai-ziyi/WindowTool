import sys, functools, inspect
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel
from typing import Any, Callable, Optional

class ButtonboxWindow(QWidget):
    def __init__(self, exited_callback_func, clicked_callback_func, button_texts, tip_text, title, window_position, window_size):
        super().__init__()
        self.clicked_callback = clicked_callback_func
        self.exited_callback = exited_callback_func
        self.record_info = []  # 记录的信息，用于主函数返回
        self.initUI(button_texts, tip_text, title, window_position, window_size)

    def initUI(self, button_texts, tip_text, title, window_position, window_size):
        self.setWindowTitle(title)  # 设置窗口标题
        self.setGeometry(window_position[0], window_position[1], window_size[0], window_size[1])  # 设置窗口位置和大小

        main_layout = QVBoxLayout()

        label_text = QLabel(tip_text)
        main_layout.addWidget(label_text)
        button_layout = QHBoxLayout()
        for index, text in enumerate(button_texts):
            button_obj = QPushButton(text)
            button_layout.addWidget(button_obj)
            button_obj.clicked.connect(functools.partial(self.private_slots_func, index, text))
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def private_slots_func(self, index, text):
        self.record_info.append((index, text))
        # 获取函数所需参数
        parameter_count = len(inspect.signature(self.clicked_callback).parameters)
        # 定义全部参数
        parameters = (index, text, self.close)
        # 目前传递的参数
        now_parameters = parameters[:parameter_count]  # 裁切区间：[)
        # 解包参数并传递
        self.clicked_callback(*now_parameters)

    def closeEvent(self, event):
        if len(inspect.signature(self.exited_callback).parameters):  # 获取函数所需参数数量
            self.exited_callback(event)
        else:
            self.exited_callback()


def main(app_object:QApplication|None=None, run_app_exec:bool=False, exited_callback_func:Callable[[Optional[object]], Any]|None=None, clicked_callback_func:Callable[[Optional[int], Optional[str], Optional[Callable[[], bool]]], Any]|None=None, button_texts:tuple[str, ...]=("按钮1", "按钮2", "按钮3", "按钮4"), tip_text:str="提示文本", title:str="标题", window_position:tuple[int, int]=(0, 0), window_size:tuple[int, int]=(1000, 618)) -> tuple[QApplication, list|None, int|None]:
    '''
    显示按钮选择窗口
    Parameters:
        app_object(QApplication|None):
            应用程序对象，为None时自动创建 | 默认值：None
        run_app_exec(bool):
            是否运行应用程序事件循环 | 默认值：False
        exited_callback_func( ( (object|None)->Any ) | None ):
            窗口被关闭时调用此函数，如果可以，传递事件对象（event）作为参数
        clicked_callback_func( ( (int|None, str|None, (()->bool)|None ) -> Any) | None ):
            任意按钮被点击时调用此函数，如果可以，传递下列参数：\n
                index(int): 当前按钮的下标\n
                text(str): 当前按钮的文本\n
                quit(function): 关闭当前窗口\n
        button_texts(tuple[str]):
            按钮的文本
        tip_text(str):
            窗口顶部提示文本
        title(str):
            窗口标题
        window_position(tuple[int]):
            窗口位置：(x, y)
        window_size(tuple[int]):
            窗口大小：(宽, 高)
    Returns:
        out(tuple[QApplication, list|None, int]):
            元祖，分别为：
                1) 应用程序对象
                2) 用户的选择，未选择时该项为空。若 run_app_exec 为 False，则该项为 None
                3) 应用程序事件循环返回值。若 run_app_exec 为 False，则该项为 None
    '''
    if app_object is None:
        app_object = QApplication(sys.argv)
    if clicked_callback_func is None:
        def func1(index:int|None, text:str|None, quit:Callable|None):
            print(f"callback: {index} | {text}")
            if quit:
                quit()
        clicked_callback_func = func1
    if exited_callback_func is None:
        def func2(event):
            print('exited')
        exited_callback_func = func2

    obj = ButtonboxWindow(exited_callback_func, clicked_callback_func, button_texts, tip_text, title, window_position, window_size)
    obj.show()
    if run_app_exec:
        code = app_object.exec()
        return (app_object, obj.record_info, code)
    return (app_object, None, None)


if __name__ == '__main__':
    obj = main(run_app_exec=True, title=" ")
    print(obj)
