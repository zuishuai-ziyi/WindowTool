import logging, enum, time
from typing import Any

class LogLevel(enum.StrEnum):
    DEBUG = enum.auto()
    TRACE = enum.auto()
    INFO = enum.auto()
    WARNING = enum.auto()
    ERROR = enum.auto()
    CRITICAL = enum.auto()

class Log:
    def __init__(
            self,
            output_to_console: bool = True,
            output_to_file: str | None = None,
            multi_line_change: bool = True,
            format_str: tuple[str, str] = (
                '[{level}] {message}',  # 控制台文本格式
                '{level: <8} ({time_h}:{time_m}:{time_s}) ==> {message}'  # 日志文件文本格式
            )
        ) -> None:
        '''
        Parameters:
            output_to_console(bool):
                是否输出日志到控制台 | 该选项会被输出日志时设置的值覆盖
            output_to_file(str | None):
                输出到的日志文件路径，若要不输出到文件，请提供 None | 该选项会被输出日志时设置的值覆盖
            multi_line_change(bool):
                是否改变多行文本的显示方式，使其美观输出
            format_str(tuple[str, str]):
                控制台文本格式 和 日志文件文本格式，允许使用 {level} {message} {time_h} {time_m} {time_s} 作为占位符
        Returns:
            out(NoneType):
                无返回值
        '''
        self.output_to_console = output_to_console
        self.output_to_file = output_to_file
        self.multi_line_change = multi_line_change
        self.format_str = format_str

    def _output(self, level: LogLevel, *message: Any, output_to_console: bool | None = None, output_to_file: str | None = None):
        if output_to_console is None:
            output_to_console = self.output_to_console
        if output_to_file is None:
            output_to_file = self.output_to_file
        
        output_message  = []
        for string in self.format_str:
            string = \
                f"{string}".format(
                    level=str(level).upper(),
                    message=' '.join(str(n) for n in message),
                    time_h=time.strftime('%H'),
                    time_m=time.strftime('%M'),
                    time_s=time.strftime('%S')
                )
            # 美观输出多行文本
            if self.multi_line_change and '\n' in string:
                string = f"""\
{string.strip('\n').replace('\n', '\n|  ')}\n\
"""
            output_message.append(string+'\n')
            

        if output_to_file is not None:
            with open(output_to_file, 'a+', encoding='utf-8') as f:
                f.write(output_message[1])
        if output_to_console:
            print(output_message[0])

    def __call__(self, *message: Any, output_to_console: bool | None = None, output_to_file: str | None = None):
        self._output(LogLevel.INFO, *message, output_to_console=output_to_console, output_to_file=output_to_file)

    def log(self, *message: Any, output_to_console: bool | None = None, output_to_file: str | None = None):
        self._output(LogLevel.INFO, *message, output_to_console=output_to_console, output_to_file=output_to_file)
    
    def trace(self, *message: Any, output_to_console: bool | None = None, output_to_file: str | None = None):
        self._output(LogLevel.TRACE, *message, output_to_console=output_to_console, output_to_file=output_to_file)
    
    def debug(self, *message: Any, output_to_console: bool | None = None, output_to_file: str | None = None):
        self._output(LogLevel.DEBUG, *message, output_to_console=output_to_console, output_to_file=output_to_file)
    
    def info(self, *message: Any, output_to_console: bool | None = None, output_to_file: str | None = None):
        self._output(LogLevel.INFO, *message, output_to_console=output_to_console, output_to_file=output_to_file)
    
    def warning(self, *message: Any, output_to_console: bool | None = None, output_to_file: str | None = None):
        self._output(LogLevel.WARNING, *message, output_to_console=output_to_console, output_to_file=output_to_file)
    
    def error(self, *message: Any, output_to_console: bool | None = None, output_to_file: str | None = None):
        self._output(LogLevel.ERROR, *message, output_to_console=output_to_console, output_to_file=output_to_file)
    
    def critical(self, *message: Any, output_to_console: bool | None = None, output_to_file: str | None = None):
        self._output(LogLevel.CRITICAL, *message, output_to_console=output_to_console, output_to_file=output_to_file)


if __name__ == "__main__":
    obj = Log(output_to_file='log.log')
    obj.log('test')
    obj.warning('warning')
    obj.error('error')
    obj.critical('critical')
    obj('info')
    obj.error(r'''Traceback (most recent call last):
  File "d:\desktop\temp\WindowTool-mer-mer\log.py", line 101, in <module>
    obj.log('test')
    ~~~~~~~^^^^^^^^
  File "d:\desktop\temp\WindowTool-mer-mer\log.py", line 78, in log
    self._output(LogLevel.INFO, *message, output_to_console=output_to_console, output_to_file=output_to_file)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "d:\desktop\temp\WindowTool-mer-mer\log.py", line 72, in _output
    print(output_message[1])
          ~~~~~~~~~~~~~~^^^
IndexError: list index out of range''')
