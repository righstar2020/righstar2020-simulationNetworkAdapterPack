#!/bin/bash
current_dir=`pwd`
# 初始化sFlow参数变量
mininet_topo_id="mini-topologies/Aarnet"
mininet_topo_name="Aarnet"
stop=0
cli=0
# 遍历所有参数
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --path)
            current_dir="$2"
            shift # past argument
            ;;
        --name)
            mininet_topo_name="$2"
            shift # past argument
            ;;
        --stop)
            stop=1
            shift # past argument
            ;;
        --cli)
            cli=1
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
client_daemon_file_path=$current_dir/../client/main.py
start_mininet() {
    if [ -f $parent_dir/network/mininet-topo/mini-topologies-done/$mininet_topo_name.py ]; then
        python $parent_dir/network/mininet-topo/mini-topologies-done/$mininet_topo_name.py $client_daemon_file_path
        echo 'mininet topo '$mininet_topo_name' has started!'
        return 0
    else
        echo 'can no find topo file:' 
        echo $parent_dir/network/mininet-topo/mini-topologies-done/$mininet_topo_name.py
        return 1
    fi
}
start_mininet_cli() {
    if [ -f $parent_dir/network/mininet-topo/mini-topologies-done/$mininet_topo_name.py ]; then
        python $parent_dir/network/mininet-topo/mini-topologies-done/$mininet_topo_name.py $client_daemon_file_path
        echo 'mininet topo '$mininet_topo_name' has started!'
        return 0
    else
        echo 'can no find topo file:' 
        echo $parent_dir/network/mininet-topo/mini-topologies-done/$mininet_topo_name.py
        return 1
    fi
}
stop_mininet() {
    mn -c >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        return 1
    else    
        echo 'mininet stopped.'
        return 0
    fi
}
if [ $cli -eq 1 ]; then
    if ! start_mininet_cli; then
        echo 'mininet_cli did not start.'
        exit 1 
    fi
    exit 0
fi

if [ $stop -eq 0 ]; then
    if ! start_mininet; then
        echo 'mininet did not start.'
        exit 1 
    fi
else
    if ! stop_mininet; then
        echo 'mininet did not stopped.'
        exit 1 
    fi
fi

