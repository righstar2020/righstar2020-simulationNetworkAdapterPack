
### mininet连接局域网网络
清除网卡ip
```shell
ifconfig ens35 0.0.0.0
```
交换机s1进行桥接之后需要pingall 重新连通h1
```python
# 检查eth1或者其他指定的网卡资源是不是已经被占用
def checkIntf( intf ):
    "Make sure intf exists and is not configured."
    if ( ' %s:' % intf ) not in quietRun( 'ip link show' ):
        error( 'Error:', intf, 'does not exist!\n' )
        exit( 1 )
    ips = re.findall( r'\d+\.\d+\.\d+\.\d+', quietRun( 'ifconfig ' + intf ) )
    if ips:
        error( 'Error:', intf, 'has an IP address,'
               'and is probably in use!\n' )
        exit( 1 )
    
#try to get hw intf from the command line; by default, use eth1
intfName = sys.argv[ 1 ] if len( sys.argv ) > 1 else 'ens35'
info( '*** Connecting to hw intf: %s' % intfName )
info( '*** Checking', intfName, '\n' )
checkIntf( intfName )
switch = net.switches[ 0 ] # 取第一个交换机与eth1桥接
info( '*** Adding hardware interface', intfName, 'to switch', switch.name, '\n' )
_intf = Intf( intfName, node=switch )
info( '[1;36m*** Add hosts[0m\n')
```