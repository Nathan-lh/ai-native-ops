# -*- coding: utf-8 -*-
"""
生成 24 篇结构化故障手册（4 类设备 × 6 类故障的矩阵）
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MANUAL_DIR = BASE_DIR / "manuals"
MANUAL_DIR.mkdir(parents=True, exist_ok=True)


# 每篇手册统一字段：
# id / device_type / fault_type / fault_phenomenon / telemetry_signature
# possible_causes / troubleshoot_steps / repair_method / severity / source
MANUALS = [
    # ==================== 空调 × 6 ====================
    {
        "id": "ac_heat_001",
        "device_type": "空调",
        "fault_type": "散热故障",
        "fault_phenomenon": "空调运行中温度持续升高，出风口温度偏高，压缩机频繁启停，可能触发高温告警。",
        "telemetry_signature": "temperature 呈线性爬升，持续超过 fault_threshold；current 可能同步升高。",
        "possible_causes": [
            "冷凝器积尘严重，换热效率下降",
            "散热风扇转速不足或损坏",
            "制冷剂不足或存在泄漏",
            "机房环境温度过高或通风不良"
        ],
        "troubleshoot_steps": [
            "检查冷凝器是否积尘，必要时清洗",
            "测量散热风扇电压与转速，判断是否损坏",
            "检查制冷剂压力是否在正常范围",
            "检查机房环境温度与通风条件"
        ],
        "repair_method": "清洗冷凝器；更换损坏风扇；补充制冷剂并排查泄漏；改善通风或增加辅助散热。",
        "severity": "中",
        "source": "自建运维手册"
    },
    {
        "id": "ac_humidity_001",
        "device_type": "空调",
        "fault_type": "湿度过高",
        "fault_phenomenon": "空调周边湿度持续偏高，送风含湿量大，设备表面可能结露。",
        "telemetry_signature": "humidity 持续超过 warn_threshold，严重时超过 fault_threshold。",
        "possible_causes": [
            "除湿功能失效或未开启",
            "排水管堵塞导致冷凝水排出不畅",
            "环境本身湿度过高",
            "温湿度传感器漂移"
        ],
        "troubleshoot_steps": [
            "检查空调除湿模式是否正常",
            "检查排水管是否堵塞",
            "对比其他温湿度传感器数据，排除传感器漂移",
            "检查房间密封与新风系统"
        ],
        "repair_method": "修复除湿功能；疏通排水管；校准或更换传感器；加强通风或增加除湿设备。",
        "severity": "中",
        "source": "自建运维手册"
    },
    {
        "id": "ac_overload_001",
        "device_type": "空调",
        "fault_type": "过载",
        "fault_phenomenon": "空调运行电流持续偏高，压缩机频繁热保护，甚至跳闸。",
        "telemetry_signature": "current 持续高于 fault_threshold；temperature 同步偏高。",
        "possible_causes": [
            "压缩机负载过大或机械卡涩",
            "电源电压偏低导致电流增大",
            "冷凝器散热不良造成高压",
            "启动电容老化导致启动电流过大"
        ],
        "troubleshoot_steps": [
            "测量供电电压是否正常",
            "检查压缩机运转声音与机械阻力",
            "检查冷凝器是否积尘",
            "测量启动电容容量是否衰减"
        ],
        "repair_method": "修复供电电压；检修或更换压缩机；清洗冷凝器；更换启动电容。",
        "severity": "高",
        "source": "自建运维手册"
    },
    {
        "id": "ac_voltage_001",
        "device_type": "空调",
        "fault_type": "电压不稳",
        "fault_phenomenon": "空调供电电压周期性抖动，压缩机启停异常，室内机指示灯闪烁。",
        "telemetry_signature": "voltage 周期性上下抖动，波动幅度超过正常范围。",
        "possible_causes": [
            "供电线路接触不良或端子氧化",
            "同一线路大功率设备频繁启停",
            "稳压器或滤波模块故障",
            "空开或接触器老化"
        ],
        "troubleshoot_steps": [
            "测量空调输入端电压波动范围",
            "检查接线端子是否松动或氧化",
            "排查同线路其他大功率设备",
            "检查稳压器与空开状态"
        ],
        "repair_method": "紧固或更换端子；调整大功率设备启停策略；维修稳压器；更换老化空开。",
        "severity": "中",
        "source": "自建运维手册"
    },
    {
        "id": "ac_wear_001",
        "device_type": "空调",
        "fault_type": "机械磨损",
        "fault_phenomenon": "空调运行噪声增大，风扇或压缩机振动明显，长期运行可能导致轴承损坏。",
        "telemetry_signature": "vibration 持续增大，可能呈阶梯式或线性上升；噪声异常。",
        "possible_causes": [
            "风扇轴承磨损或润滑不足",
            "压缩机内部磨损",
            "风轮不平衡或有异物",
            "固定螺栓松动"
        ],
        "troubleshoot_steps": [
            "听音判断异响来源（风扇 or 压缩机）",
            "检查风扇轴承润滑与间隙",
            "检查风轮是否积尘失衡",
            "紧固固定螺栓"
        ],
        "repair_method": "补充或更换润滑脂；更换轴承；清理或更换风轮；紧固螺栓。",
        "severity": "中",
        "source": "自建运维手册"
    },
    {
        "id": "ac_offline_001",
        "device_type": "空调",
        "fault_type": "掉线",
        "fault_phenomenon": "空调控制器与平台失去通信，遥测中断，无法远程控制。",
        "telemetry_signature": "无新 telemetry 写入；device_latest_status.last_seen 长时间未更新。",
        "possible_causes": [
            "通信模块故障或网线松动",
            "空调断电或空开跳闸",
            "MQTT 客户端异常退出",
            "IP 地址冲突"
        ],
        "troubleshoot_steps": [
            "检查空调是否断电",
            "检查通信模块指示灯与网线",
            "检查 MQTT 客户端日志",
            "检查 IP 地址冲突"
        ],
        "repair_method": "恢复供电；重新插拔网线或更换通信模块；重启 MQTT 客户端；修复 IP 冲突。",
        "severity": "中",
        "source": "自建运维手册"
    },

    # ==================== 电机 × 6 ====================
    {
        "id": "motor_overload_001",
        "device_type": "电机",
        "fault_type": "过载",
        "fault_phenomenon": "电机电流突增或持续偏高，转速下降，机身温度升高，可能伴随异响。",
        "telemetry_signature": "current 突增或持续高于 fault_threshold；temperature 同步上升。",
        "possible_causes": [
            "负载机械阻力过大",
            "轴承卡涩或损坏",
            "电压过低导致电流增大",
            "电机绕组局部短路"
        ],
        "troubleshoot_steps": [
            "检查负载端是否卡死或异物阻塞",
            "手动盘车判断轴承是否卡涩",
            "测量供电电压是否正常",
            "测量绕组绝缘电阻与直流电阻"
        ],
        "repair_method": "清理负载异物；更换轴承；修复供电电压；重绕或更换电机绕组。",
        "severity": "高",
        "source": "自建运维手册"
    },
    {
        "id": "motor_wear_001",
        "device_type": "电机",
        "fault_type": "机械磨损",
        "fault_phenomenon": "电机振动幅度持续增大，噪声变大，长期运行可能引起轴承损坏。",
        "telemetry_signature": "vibration 持续增大，可能呈阶梯式或线性上升。",
        "possible_causes": [
            "轴承磨损或润滑不足",
            "联轴器对中不良",
            "转子动平衡破坏",
            "地脚螺栓松动"
        ],
        "troubleshoot_steps": [
            "检查轴承润滑与间隙",
            "检查联轴器对中情况",
            "检查地脚螺栓是否松动",
            "必要时做动平衡测试"
        ],
        "repair_method": "补充或更换润滑脂；更换轴承；重新对中；紧固地脚螺栓；做动平衡校正。",
        "severity": "中",
        "source": "自建运维手册"
    },
    {
        "id": "motor_heat_001",
        "device_type": "电机",
        "fault_type": "散热故障",
        "fault_phenomenon": "电机机身温度持续升高，外壳烫手，热保护频繁动作。",
        "telemetry_signature": "temperature 持续高于 fault_threshold；可能伴随 current 偏高。",
        "possible_causes": [
            "散热风扇损坏或通风口堵塞",
            "绕组绝缘老化，损耗增大",
            "环境温度过高",
            "长期过载运行"
        ],
        "troubleshoot_steps": [
            "检查散热风扇与通风口",
            "测量绕组绝缘电阻",
            "检查环境温度",
            "核对电机负载率"
        ],
        "repair_method": "更换散热风扇；清理通风口；检修或更换绕组；降低负载或改善环境。",
        "severity": "高",
        "source": "自建运维手册"
    },
    {
        "id": "motor_voltage_001",
        "device_type": "电机",
        "fault_type": "电压不稳",
        "fault_phenomenon": "电机供电电压波动，转速不稳，启停异常。",
        "telemetry_signature": "voltage 周期性抖动，波动幅度超过正常范围。",
        "possible_causes": [
            "供电线路接触不良",
            "同线路大功率设备频繁启停",
            "变频器或软启动器故障",
            "电网本身波动"
        ],
        "troubleshoot_steps": [
            "测量电机输入端电压",
            "检查接线端子",
            "检查变频器输出",
            "排查同线路负载"
        ],
        "repair_method": "紧固端子；维修变频器；调整大功率设备启停策略；必要时增加稳压装置。",
        "severity": "中",
        "source": "自建运维手册"
    },
    {
        "id": "motor_humidity_001",
        "device_type": "电机",
        "fault_type": "湿度过高",
        "fault_phenomenon": "电机运行环境湿度偏高，绕组受潮，绝缘电阻下降，可能引发短路。",
        "telemetry_signature": "humidity 持续超过 warn_threshold；绝缘电阻下降。",
        "possible_causes": [
            "环境湿度高或存在冷凝水",
            "电机防护等级不足",
            "长期停机后未做干燥处理",
            "密封件老化"
        ],
        "troubleshoot_steps": [
            "测量绕组绝缘电阻",
            "检查电机密封与防护等级",
            "检查环境湿度来源",
            "检查是否有冷凝水"
        ],
        "repair_method": "烘干绕组；更换密封件；提升防护等级；改善环境通风或增加除湿设备。",
        "severity": "高",
        "source": "自建运维手册"
    },
    {
        "id": "motor_offline_001",
        "device_type": "电机",
        "fault_type": "掉线",
        "fault_phenomenon": "电机控制器与平台失去通信，遥测中断，无法远程控制启停。",
        "telemetry_signature": "无新 telemetry 写入；last_seen 停止更新。",
        "possible_causes": [
            "控制器断电或通信模块故障",
            "网线或光纤松动",
            "MQTT 客户端异常退出",
            "IP 地址冲突"
        ],
        "troubleshoot_steps": [
            "检查控制器供电",
            "检查网线或光纤连接",
            "检查 MQTT 客户端日志",
            "排查 IP 冲突"
        ],
        "repair_method": "恢复供电；重新插拔或更换通信线缆；重启 MQTT 客户端；修复 IP 冲突。",
        "severity": "中",
        "source": "自建运维手册"
    },

    # ==================== 配电柜 × 6 ====================
    {
        "id": "cabinet_voltage_001",
        "device_type": "配电柜",
        "fault_type": "电压不稳",
        "fault_phenomenon": "配电柜输出电压周期性抖动，照明闪烁，敏感设备可能重启。",
        "telemetry_signature": "voltage 周期性上下抖动，波动幅度超过正常范围。",
        "possible_causes": [
            "输入电源波动或接触不良",
            "稳压器或调压模块故障",
            "接线端子松动",
            "大功率设备频繁启停造成冲击"
        ],
        "troubleshoot_steps": [
            "测量输入电压是否稳定",
            "检查接线端子是否松动或氧化",
            "检查稳压器工作状态",
            "排查大功率设备启停规律"
        ],
        "repair_method": "紧固或更换端子；维修稳压器；调整大功率设备启停策略；必要时增加稳压装置。",
        "severity": "高",
        "source": "自建运维手册"
    },
    {
        "id": "cabinet_overload_001",
        "device_type": "配电柜",
        "fault_type": "过载",
        "fault_phenomenon": "配电柜总电流持续偏高，柜内温度上升，断路器可能发热或跳闸。",
        "telemetry_signature": "current 持续高于 fault_threshold；temperature 同步上升。",
        "possible_causes": [
            "后端负载过多",
            "线路老化导致电阻增大",
            "断路器规格偏小",
            "存在短路或漏电"
        ],
        "troubleshoot_steps": [
            "统计后端负载总功率",
            "测量线路绝缘与漏电流",
            "检查断路器规格与温度",
            "检查是否存在短路点"
        ],
        "repair_method": "减少负载或扩容；更换老化线路；更换合适断路器；排查并修复短路漏电点。",
        "severity": "高",
        "source": "自建运维手册"
    },
    {
        "id": "cabinet_heat_001",
        "device_type": "配电柜",
        "fault_type": "散热故障",
        "fault_phenomenon": "配电柜内部温度持续升高，柜体发烫，断路器可能因高温误动作。",
        "telemetry_signature": "temperature 持续高于 fault_threshold；可能伴随 current 偏高。",
        "possible_causes": [
            "散热风扇损坏或通风口堵塞",
            "柜内积尘严重",
            "环境温度过高",
            "负载长期偏高"
        ],
        "troubleshoot_steps": [
            "检查柜内散热风扇",
            "检查通风口与滤网",
            "测量柜内各点温度",
            "核对负载率"
        ],
        "repair_method": "更换散热风扇；清理通风口与滤网；改善环境通风；降低负载或增加散热装置。",
        "severity": "高",
        "source": "自建运维手册"
    },
    {
        "id": "cabinet_humidity_001",
        "device_type": "配电柜",
        "fault_type": "湿度过高",
        "fault_phenomenon": "配电柜内部湿度偏高，柜内壁或母排出现凝露，绝缘下降。",
        "telemetry_signature": "humidity 持续超过 warn_threshold；绝缘电阻下降。",
        "possible_causes": [
            "柜体密封不良，湿气进入",
            "环境湿度高",
            "加热除湿装置失效",
            "电缆沟潮气上升"
        ],
        "troubleshoot_steps": [
            "检查柜体密封",
            "检查加热除湿装置",
            "检查电缆沟封堵",
            "测量绝缘电阻"
        ],
        "repair_method": "修复密封；更换加热除湿装置；封堵电缆沟；加强通风或增加除湿设备。",
        "severity": "高",
        "source": "自建运维手册"
    },
    {
        "id": "cabinet_offline_001",
        "device_type": "配电柜",
        "fault_type": "掉线",
        "fault_phenomenon": "配电柜监控终端与平台失去通信，遥测中断，无法远程查看电气参数。",
        "telemetry_signature": "无新 telemetry 写入；last_seen 停止更新。",
        "possible_causes": [
            "监控终端断电",
            "通信模块故障或网线松动",
            "MQTT 客户端异常退出",
            "IP 地址冲突"
        ],
        "troubleshoot_steps": [
            "检查监控终端供电",
            "检查通信模块与网线",
            "检查 MQTT 客户端日志",
            "排查 IP 冲突"
        ],
        "repair_method": "恢复供电；更换通信模块或网线；重启 MQTT 客户端；修复 IP 冲突。",
        "severity": "中",
        "source": "自建运维手册"
    },
    {
        "id": "cabinet_wear_001",
        "device_type": "配电柜",
        "fault_type": "机械磨损",
        "fault_phenomenon": "配电柜断路器操动机构机械磨损，分合闸卡涩或声音异常。",
        "telemetry_signature": "无明显遥测异常；操作记录中分合闸时间可能变长。",
        "possible_causes": [
            "断路器操动机构长期使用磨损",
            "润滑不足",
            "弹簧机构疲劳",
            "机械连杆变形"
        ],
        "troubleshoot_steps": [
            "检查断路器分合闸动作",
            "检查操动机构润滑",
            "检查弹簧机构",
            "检查连杆是否变形"
        ],
        "repair_method": "补充润滑；更换磨损部件；更换弹簧；校正或更换连杆。",
        "severity": "中",
        "source": "自建运维手册"
    },

    # ==================== 温湿度传感器 × 4 ====================
    {
        "id": "sensor_offline_001",
        "device_type": "温湿度传感器",
        "fault_type": "掉线",
        "fault_phenomenon": "温湿度传感器长时间无数据上报，平台显示离线或 last_seen 长时间未更新。",
        "telemetry_signature": "无新 telemetry 写入；device_latest_status.last_seen 停止更新。",
        "possible_causes": [
            "电池电量耗尽",
            "网络信号弱或网关故障",
            "传感器硬件损坏",
            "MQTT 客户端掉线未重连"
        ],
        "troubleshoot_steps": [
            "检查电池电压或供电",
            "检查网关与信号强度",
            "替换同型号传感器验证",
            "查看 MQTT 连接日志"
        ],
        "repair_method": "更换电池；修复网络或网关；更换传感器；修复 MQTT 重连逻辑。",
        "severity": "低",
        "source": "自建运维手册"
    },
    {
        "id": "sensor_voltage_001",
        "device_type": "温湿度传感器",
        "fault_type": "电压不稳",
        "fault_phenomenon": "传感器供电电压波动，数据上报断断续续，或读数异常跳变。",
        "telemetry_signature": "上报不连续；读数偶发跳变。",
        "possible_causes": [
            "电池电量不足",
            "供电线路接触不良",
            "电源适配器故障",
            "电磁干扰"
        ],
        "troubleshoot_steps": [
            "测量电池或适配器电压",
            "检查供电端子",
            "更换电源适配器",
            "排查电磁干扰源"
        ],
        "repair_method": "更换电池或电源适配器；紧固端子；远离干扰源或增加屏蔽。",
        "severity": "低",
        "source": "自建运维手册"
    },
    {
        "id": "sensor_humidity_001",
        "device_type": "温湿度传感器",
        "fault_type": "湿度过高",
        "fault_phenomenon": "传感器探头长期处于高湿环境，读数偏高或漂移，甚至短路失效。",
        "telemetry_signature": "humidity 读数长期异常偏高；可能偏离其他传感器读数。",
        "possible_causes": [
            "探头受潮或结露",
            "探头防护涂层老化",
            "安装位置靠近水源",
            "环境长期高湿"
        ],
        "troubleshoot_steps": [
            "检查探头是否有凝露",
            "对比其他传感器读数",
            "检查安装位置",
            "检查防护涂层"
        ],
        "repair_method": "烘干探头；更换探头；更换防护等级更高的型号；调整安装位置。",
        "severity": "中",
        "source": "自建运维手册"
    },
    {
        "id": "sensor_drift_001",
        "device_type": "温湿度传感器",
        "fault_type": "数据漂移",
        "fault_phenomenon": "传感器读数与标准值偏差逐渐增大，长时间未校准。",
        "telemetry_signature": "读数与同环境其他传感器差异持续增大。",
        "possible_causes": [
            "探头老化",
            "长期未校准",
            "环境污染（粉尘、腐蚀气体）",
            "供电电压不稳定"
        ],
        "troubleshoot_steps": [
            "与标准仪器对比读数",
            "检查探头污染情况",
            "检查供电电压",
            "查看上次校准时间"
        ],
        "repair_method": "重新校准；清洁或更换探头；稳定供电；缩短校准周期。",
        "severity": "低",
        "source": "自建运维手册"
    },

    # ==================== 通用 × 2 ====================
    {
        "id": "common_offline_001",
        "device_type": "通用",
        "fault_type": "掉线",
        "fault_phenomenon": "设备心跳丢失，遥测数据中断，平台无法获取最新状态。",
        "telemetry_signature": "telemetry 中断；last_seen 超过预期上报周期。",
        "possible_causes": [
            "设备断电",
            "网络中断",
            "MQTT Broker 连接失败",
            "设备固件死机"
        ],
        "troubleshoot_steps": [
            "确认设备是否断电",
            "检查网络链路与交换机",
            "检查 EMQX 连接状态",
            "尝试重启设备"
        ],
        "repair_method": "恢复供电；修复网络；重启 MQTT 客户端；升级或重启设备固件。",
        "severity": "中",
        "source": "自建运维手册"
    },
    {
        "id": "common_power_001",
        "device_type": "通用",
        "fault_type": "电源故障",
        "fault_phenomenon": "设备频繁重启或无法开机，供电异常。",
        "telemetry_signature": "设备启动记录频繁；上报数据断断续续。",
        "possible_causes": [
            "电源模块损坏",
            "供电电压异常",
            "电源线接触不良",
            "电源容量不足"
        ],
        "troubleshoot_steps": [
            "测量供电电压",
            "检查电源模块输出",
            "检查电源线连接",
            "核对设备功耗与电源容量"
        ],
        "repair_method": "更换电源模块；稳定供电；重新插拔或更换电源线；更换容量更大的电源。",
        "severity": "高",
        "source": "自建运维手册"
    }
]


def main():
    # 清空旧手册目录（避免残留旧的 8 篇）
    for old_file in MANUAL_DIR.glob("*.json"):
        old_file.unlink()

    all_manuals = []
    for manual in MANUALS:
        file_path = MANUAL_DIR / f"{manual['id']}.json"
        file_path.write_text(
            json.dumps(manual, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        all_manuals.append(manual)

    merged_path = BASE_DIR / "manuals_all.json"
    merged_path.write_text(
        json.dumps(all_manuals, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"已生成 {len(MANUALS)} 篇故障手册")
    print(f"单篇目录：{MANUAL_DIR}")
    print(f"合并文件：{merged_path}")


if __name__ == "__main__":
    main()