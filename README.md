# 窗口管理工具

- 本工具由 python 编写，旨在获取并更改窗口信息。

## 运行环境

- Windows 10/11
- Python 3

## 功能简介

### 获取信息

1. 窗口句柄
2. 窗口标题
3. 窗口位置(相对于屏幕原点)
4. 窗口大小
5. 窗口所在进程PID
6. 窗口所在进程可执行文件位置

### 进行操作

1. **强制结束**窗口所在进程
2. **强制删除**窗口所在进程**源文件**(需先结束进程)
3. **挂起**窗口所在进程
4. **运行**窗口所在进程**源文件**
5. 使窗口**无边框化**
6. **恢复**窗口**边框**
7. 改变窗口状态(**最大化 最小化** 恢复)
8. **隐藏 / 显示** 窗口
9. 更改窗口**位置 / 大小**

### 其他

1. 运行外部程序。这将调用系统的运行对话框
2. 当前窗口可使用 UIAccess 权限**强制置顶**，覆盖其他置顶窗口(或许可以对抗流氓软件？)
3. 支持保存窗口信息，选中相同窗口时会自动沿用上次退出时的属性

### 更新日志

#### v1.0.0

首个发布版本

#### v1.1.0

增加调整窗口 位置/大小/标题 功能

修复部分BUG，优化代码

#### v1.1.1

修复CPU占用过高的问题

修复部分BUG，优化代码

#### v1.2.0

新增 以 UIAccess 权限置顶 的功能，核心代码来自 shc0743 的项目 https://github.com/shc0743/RunUIAccess

使界面尺寸可被修改

自动记录窗口属性：选中窗口时加载上次选中此窗口时设置的信息

新增日志记录功能

![GitHub Repo stars](https://img.shields.io/github/stars/zuishuai-ziyi/WindowTool) ![GitHub followers](https://img.shields.io/github/followers/zuishuai-ziyi) ![GitHub forks](https://img.shields.io/github/forks/zuishuai-ziyi/WindowTool)


