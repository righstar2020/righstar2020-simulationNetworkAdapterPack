
from command import execute_cmd_thread
from file_util import get_project_root_path
import os
current_dir = get_project_root_path()
def start_simulator():
    pass
def check_mininet_started():
    
    pass
def check_ryu_started():
    pass

def check_sflow_started():
    pass
def start_mininet():
    pass

def start_ryu_app():
    pass

def start_sflow():
    global current_dir
    execute_cmd_thread(current_dir+"/cmd/start_sflow.sh")
    pass

def stop_simulator():
    global current_dir
    execute_cmd_thread(current_dir+"/cmd/stop_sflow.sh")
    pass

if __name__ == '__main__':
    start_sflow()
    pass