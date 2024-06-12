#!/bin/bash
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
if ! stop_sflow; then
    echo 'sFlow agent did not stop.'
    exit 1 
fi