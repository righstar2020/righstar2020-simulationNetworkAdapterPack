#!/bin/bash
current_dir=`pwd`
# 初始化sFlow参数变量
agent="s1-eth0"
controller_ip="127.0.0.1"
controller_port="6343"
bridge="s1"
sampling="10"
polling="20"
stop=0
# 遍历所有参数
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --path)
            current_dir="$2"
            shift # past argument
            ;;
        --agent)
            agent="$2"
            shift # past argument
            ;;
        --ip)
            controller_ip="$2"
            shift # past argument
            ;;
        --port)
            controller_port="$2"
            shift # past argument
            ;;
        --bridge)
            bridge="$2"
            shift # past argument
            ;;
        --sampling)
            sampling="$2"
            shift # past argument
            ;;
        --polling)
            polling="$2"
            shift # past argument
            ;;
        --stop)
            stop=1
            shift # past argument
            ;;
        *)
            # 如果不认识的参数，可以处理错误或者忽略
            echo "Unknown option: $1"
            ;;
    esac
    shift # past argument or value
done
parent_dir=`dirname $current_dir`
#开启sFlow监控
start_sflow() {
    #sflow
    if [ -f $parent_dir/network/sflow-rt/start.sh ]; then
        nohup $parent_dir/network/sflow-rt/start.sh &
        echo 'sflow has started!'
        return 0
    else
        echo 'can no find sflow:' 
        echo $parent_dir/network/sflow-rt/start.sh
        return 1
    fi
}
start_sflow_agent() {
    #判断命令是否存在
    type ovs-vsctl >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "ovs-vsctl is not found or has an error. Attempting to configure sFlow..."
        return 1
    else
        ovs-vsctl -- --id=@sflow create sflow agent=$agent target=\"$controller_ip:$controller_port\" sampling=$sampling polling=$polling -- -- set bridge $bridge sflow=@sflow
        echo 'sFlow agent started.'
        return 0
    fi
}
stop_sflow() {
    #sflow开放在8008端口(删除所有8008端口的进程)
    lsof -ti :8008| xargs kill -9 >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        return 1
    else    
        echo 'sFlow agent stopped.'
        return 0
    fi
}
if [ $stop -eq 0 ]; then
    # 调用start_sflow函数并检查返回值
    if ! start_sflow; then
        echo 'sFlow did not start. '
        exit 1 
    fi
    # 调用start_sflow函数并检查返回值
    if ! start_sflow_agent; then
        echo 'sFlow agent did not start. '
        exit 1 
    fi
else
    if ! stop_sflow; then
    echo 'sFlow agent did not stop.'
    exit 1 
    fi
fi