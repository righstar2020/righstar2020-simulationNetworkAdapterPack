#!/bin/bash
current_dir=`pwd`
# 初始化sFlow参数变量
app_name="ddos_simulation_app.py"
stop=0
# 遍历所有参数
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --path)
            current_dir="$2"
            shift # past argument
            ;;
        --app_name)
            app_name="$2"
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

#启动ryu控制器
start_ryu_with_app() {
    app_file_path=$current_dir/../network/ryu-app/$app_name 
    #find ryu-manager
    type ryu-manager >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "ryu-manager is not found or has an error. "
        return 1
    else
        if [ -f $app_file_path ]; then
            nohup ryu-manager $app_file_path &
            return 0
        else
            echo "can no find ryu app!:" "$app_file_path"
            return 1
        fi
    fi
    
}
#关闭ryu控制器
stop_ryu() {
    #ryu开放在8080端口(删除所有8080端口的进程)
    lsof -ti :8080| xargs kill -9 >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        return 1
    else    
        echo 'ryu app stopped.'
        return 0
    fi
}

if [ $stop -eq 0 ]; then
    # 调用start_sflow函数并检查返回值
    if ! start_ryu_with_app; then
        echo 'ryu app did not start!'
        exit 1 
    fi
else
    echo 'ryu app stopped!'
fi


