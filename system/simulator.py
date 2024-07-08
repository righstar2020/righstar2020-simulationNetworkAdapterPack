
from system.command import execute_cmd_thread,execute_cmd_list_thread,execute_cmd_nowait,execute_cmd_list_sync
from system.command import execute_cmd,open_terminal_execute_cmd,open_gnome_terminal_execute_cmd
from system.file_util import get_project_root_path,read_all_json_from_path
import asyncio
from db.tiny_db import TinyDBUtil
project_dir = get_project_root_path()
topo_data = {}
current_topo_name = ''
current_topo_id = ''
current_topo_dynamic_data = {}
dbUtil = TinyDBUtil()
"""
    数据操作方法
"""
def get_current_topo_data():
    global current_topo_name,current_topo_id,topo_data
    if topo_data.get(current_topo_name)!=None:
        return current_topo_name,current_topo_id,topo_data[current_topo_name]
    return '','',{}
def get_current_topo_dynamic_data():
    global current_topo_dynamic_data
    return current_topo_dynamic_data
def update_current_topo_dynamic_data(data):
    global current_topo_dynamic_data
    if data!=None:
        current_topo_dynamic_data = data
        update_current_topo_data_to_db(current_topo_dynamic_data)
def insert_topo_data_to_db(topo_data):
    dbUtil.async_write("network_topo_data", topo_data)

def update_topo_data_to_db(topo_id,topo_data):
    dbUtil.async_upsert_by_key("network_topo_data", topo_data,"topo_id",topo_id)
def update_current_topo_data_to_db(topo_data):
    #更新当前网络拓扑数据
    topo_data['topo_id'] = 'current_topo'#id设置为当前网络拓扑
    dbUtil.async_upsert_by_key("network_topo_data", topo_data,"topo_id","current_topo")
"""
    仿真网络操作方法
"""
def load_topo_data():
    global project_dir
    global topo_data
    print("-------------加载拓扑数据-------------------")
    topo_data= read_all_json_from_path(project_dir+"/network/mininet-topo/mini-topologies-json")
    return topo_data
def clear_simulator():
    global project_dir
    print("-------------清理仿真网络环境-------------------")
    cmd_list = [project_dir+"/cmd/sflow.sh --stop",
                project_dir+"/cmd/ryu.sh --stop",
                project_dir+"/cmd/mininet.sh --stop"]
    execute_cmd_list_thread(cmd_list)
def start_simulator_by_topo(topo_name):
    global project_dir,current_topo_name,current_topo_id,current_topo_dynamic_data
    print(f"-------------清理仿真网络-------------------")
    current_topo_name = topo_name
    current_topo_id  = topo_data[topo_name]['topo_id']
    update_current_topo_dynamic_data(topo_data[topo_name]) #更新数据库当前网络拓扑数据
    cmd_list = [project_dir+"/cmd/sflow.sh --stop",#    1.清理仿真网络
                project_dir+"/cmd/ryu.sh --stop",
                project_dir+"/cmd/mininet.sh --stop"]
    execute_cmd_list_sync(cmd_list)
    print(f"-------------启动仿真网络 {topo_name}-------------------")
    execute_cmd_nowait(project_dir+"/cmd/ryu.sh --path "+project_dir+"/cmd")  #2.启动ryu控制器(注意转到cmd路径执行)
    open_terminal_execute_cmd(project_dir+"/cmd/mininet.sh --name "+topo_name+" --path "+project_dir+"/cmd")
    execute_cmd_thread(project_dir+"/cmd/sflow.sh "+" --path "+project_dir+"/cmd",wait_time=15) #等待15s拓扑创建完成

    
def reload_simulator_by_topo(topo_name):
    print(f"-------------仿真网络重启 {topo_name}-------------------")
    start_simulator_by_topo(topo_name)
def start_simulator():
    load_topo_data()
    start_simulator_by_topo('Aarnet')
    
    