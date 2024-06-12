
#获取当前项目根目录绝对路径
import os
import sys

def get_project_root_path():
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))