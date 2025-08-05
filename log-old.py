'''该文件较为久远，代码复杂，不建议使用'''
from loguru import logger
import traceback, time
from typing import Callable, List

class log:
    def __init__(self, save_path:str|None = None, merge_message:bool = True, one_line_len_max:int = 45) -> None:
        '''
        初始化
        Parameters:
            save_path(str|None): 默认保存路径，若使用add_log_message方法时未提供save_path，则使用此参数作为save_path（为None表示不提供默认值）
            merge_message(bool): 是否合并消息-默认，若使用add_log_message方法时未提供merge_message，则使用此参数作为merge_message，默认为True，为False时不合并同一时间戳的相同消息
            one_line_len_max(int): 单行信息最大长度
        '''
        # 验证参数
        if not(isinstance(save_path, str|None)):
            return

        # 建立变量
        self.level_list  = [
            'debug',  # 调试
            'info',  # 信息
            'warning',  # 警告
            'error',  # 错误
            'critical'  # 严重
        ]
        '''等级对应列表'''

        self.one_line_len_max = one_line_len_max
        '''日志文件单行最大长度'''

        self.t_message_list: List[float | str] = [round(time.time(), 1)]
        '''（记录的）时间戳的所有消息及时间戳（第一项为时间戳）'''

        self.save_path = save_path
        '''默认保存路径'''

        self.merge_message = merge_message
        '''是否合并消息-默认'''


    def add_log_message(self, level: int | str, message: str | int | float, save_path: str | None = None, begin_message: bool = False, end_message: bool = False, merge_message = None):
        '''新建日志信息'''
        def use_default_value(default, value):
            '''使用默认值，无默认值时使用原本值，返回应使用的值'''
            if value == None and default == None:
                # 若默认值和给定的值为空，则返回空
                return None

            if value == None:
                return default
            else:
                return value

        '''参数验证'''
        # 类型验证
        if not(isinstance(level, int|str)) or not(isinstance(message, str|int|float)) or not(isinstance(save_path, str|None)):
            return
        # 内容验证
        if isinstance(level, str) and level not in self.level_list:
            return
        if isinstance(level, int) and (level < 0 or level > 4):
            return

        # 参数归一
        message = str(message)
        if isinstance(level, str):
            # 获取level在level_list中的编号
            index_level: int = self.level_list.index(level)
        else:
            index_level = level

        '''参数处理'''
        # 处理save_path
        _save_path: str = use_default_value(self.save_path, save_path) # type: ignore
        # 处理merge_message
        merge_message = use_default_value(self.merge_message, merge_message)

        # 处理message
        if len(message) > self.one_line_len_max:
            l = []
            i = 0
            while i < len(message)-1:
                if i % self.one_line_len_max == 0:
                    l.append(message[i-self.one_line_len_max:i])
                    # 如果剩余长度不足单行最大长度，则单独分一行，并结束循环
                    if len(message[i:]) < self.one_line_len_max:
                        l.append(message[i:len(message)])
                        break
                i += 1

            # 移出第一个空项
            l.pop(0)
            # 拼接出message
            string = '\\n' + ' '*35
            message = string.join(l)

        # 自定义写入日志信息格式
        if begin_message:
            format_log = " * Start\n\n {level: <8} ({time:YYYY-MM-DD HH:mm:ss}) ==> {message}\n"
        if end_message:
            format_log = " {level: <8} ({time:YYYY-MM-DD HH:mm:ss}) ==> {message}\n\n * End\n"
        if not(begin_message or end_message):
            format_log = " {level: <8} ({time:YYYY-MM-DD HH:mm:ss}) ==> {message}\n"

        # 删除旧处理器
        logger.remove()
        # 新建日志处理器
        logger.add(_save_path, rotation='512 KB', format=format_log)  # rotation用于控制每个日志文件的最大大小

        # 移除控制台输出处理器
        try:
            logger.remove(0)  # 移除第一个处理器（即默认的控制台输出处理器）
        except Exception:
            pass
        
        '''去除同一时间戳相同的信息'''
        # 判断merge_message是否为True
        if merge_message:
            # 判断时间戳是否需要更新
            if round(time.time(), 1) != round(self.t_message_list[0], 1): # type: ignore
                print('time', self.t_message_list)
                # 使用当前时间戳替换第一位（即记录的时间戳）
                self.t_message_list[0] = round(time.time(), 1)
                # 重置列表
                self.t_message_list = [time.time()]
            # 判断当前信息是否可写入日志文件
            if message in self.t_message_list:
                print('return')
                return
            else:
                try:
                    print('append', self.t_message_list, round(self.t_message_list, 1)) # type: ignore
                except:
                    pass
                self.t_message_list.append(message)


        # 拼接出完整命令
        command = 'logger.{level}("""{text}""")'.format(level=self.level_list[index_level], text=message)
        # 运行命令
        exec(command)


    def __call__(self, level: int | str, save_path: str | None=None, begin_message: bool = False, end_message: bool = False, when_error_end_is_end_message: bool = False, when_error_end_log_level: int | str = 'warning'):
        '''返回装饰器'''
        def str_to_better(string:str):
            return string.replace('\\', '\\\\').replace('"', '\\"').replace('\'', '\\\'').strip()
        def return_func(func: Callable) -> Callable:
            def new_func(*argc, **k):
                begin_time:float = time.time()
                self.add_log_message(level=level, message=f'函数“{func.__name__}”开始运行，传入位置参数：{argc}，传入关键字参数：{k}', save_path=save_path, begin_message=begin_message)
                try:
                    func_return_value = func(*argc, *k)
                except:
                    self.add_log_message(level=when_error_end_log_level, message=f'函数“{func.__name__}”运行时发生异常：“{"\n"+" "*36}{str_to_better(traceback.format_exc()).replace("\n", "\n"+" "*36)}{"\n"+" "*36}”，函数已运行 {time.time()-begin_time} 秒', save_path=save_path, end_message=when_error_end_is_end_message)
                    raise
                self.add_log_message(level=level, message=f'函数“{func.__name__}”运行完成，耗时 {time.time()-begin_time} 秒，返回值为“{func_return_value}”，返回类型为“{type(func_return_value)}”', save_path=save_path, end_message=end_message)
                return func_return_value
            return new_func
        return return_func







# 程序入口
if __name__ == '__main__':
    obj = log('.\\abc.log', False, one_line_len_max=9999999)
    for i in range(0, 101):
        obj.add_log_message(0, 'test', '.\\temp.log', begin_message=True)
        obj.add_log_message(1, 'test', '.\\temp.log')
        obj.add_log_message(2, 'test', '.\\temp.log')
        obj.add_log_message(3, 'test', '.\\temp.log')
        obj.add_log_message(4, 'test', '.\\temp.log')
        obj.add_log_message(0, 'test', '.\\temp.log')
        obj.add_log_message(1, 'test', '.\\temp.log')
        obj.add_log_message(2, 'test', '.\\temp.log')
        obj.add_log_message(3, 'test', '.\\temp.log')
        obj.add_log_message(4, 'test', '.\\temp.log', end_message=True)
    @obj(level='debug', when_error_end_log_level='error')
    def a():
        print("a函数的运行内容...")
        time.sleep(1)
        # raise TypeError("aaa")
        print("a函数的操作完成")
    a()
