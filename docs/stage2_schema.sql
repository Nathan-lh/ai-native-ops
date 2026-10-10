-- 遥测链路相关表
USE ai_ops;

-- 实验室
CREATE TABLE IF NOT EXISTS lab_room (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    room_name VARCHAR(100) NOT NULL COMMENT '实验室名称',
    location VARCHAR(200) COMMENT '位置',
    capacity INT COMMENT '容量',
    status VARCHAR(20) DEFAULT 'IDLE' COMMENT 'IDLE/IN_USE/MAINTENANCE',
    description VARCHAR(500),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='实验室';

-- 设备
CREATE TABLE IF NOT EXISTS device (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_name VARCHAR(100) NOT NULL COMMENT '设备名称',
    device_code VARCHAR(64) NOT NULL UNIQUE COMMENT '资产编号(唯一)',
    device_type VARCHAR(50) COMMENT '设备类型',
    lab_id BIGINT COMMENT '所属实验室',
    status VARCHAR(20) DEFAULT 'NORMAL' COMMENT 'NORMAL/WARNING/FAULT',
    description VARCHAR(500),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
) COMMENT='设备';

-- 遥测历史
CREATE TABLE IF NOT EXISTS telemetry (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id BIGINT NOT NULL COMMENT '设备ID',
    temperature DECIMAL(8,2) COMMENT '温度',
    humidity DECIMAL(8,2) COMMENT '湿度',
    `current` DECIMAL(8,2) COMMENT '电流',
    voltage DECIMAL(8,2) COMMENT '电压',
    vibration DECIMAL(8,2) COMMENT '振动',
    ts DATETIME NOT NULL COMMENT '上报时间',
    KEY idx_device_ts (device_id, ts)
) COMMENT='遥测历史';

-- 设备实时状态快照
CREATE TABLE IF NOT EXISTS device_latest_status (
    device_id BIGINT PRIMARY KEY COMMENT '设备ID',
    status VARCHAR(20) COMMENT '当前状态',
    last_seen DATETIME COMMENT '最近上报时间',
    last_metric_json JSON COMMENT '最新一条遥测',
    updated_at DATETIME
) COMMENT='设备实时状态快照';

-- 健康评估规则/阈值
CREATE TABLE IF NOT EXISTS fault_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_type VARCHAR(50) COMMENT '设备类型',
    metric VARCHAR(30) COMMENT '指标:temperature/voltage/current/vibration/humidity',
    warn_threshold DECIMAL(10,2) COMMENT '预警阈值',
    fault_threshold DECIMAL(10,2) COMMENT '故障阈值',
    consecutive_count INT DEFAULT 3 COMMENT '连续N次去抖'
) COMMENT='健康评估规则';

-- 默认规则
INSERT INTO fault_rule (device_type, metric, warn_threshold, fault_threshold, consecutive_count) VALUES
('空调', 'temperature', 35.00, 45.00, 3),
('空调', 'humidity', 70.00, 85.00, 3),
('电机', 'vibration', 5.00, 10.00, 3),
('电机', 'current', 15.00, 25.00, 3),
('配电柜', 'voltage', 240.00, 260.00, 3),
('配电柜', 'current', 30.00, 50.00, 3),
('DEFAULT', 'temperature', 40.00, 50.00, 3),
('DEFAULT', 'humidity', 75.00, 90.00, 3),
('DEFAULT', 'current', 20.00, 30.00, 3),
('DEFAULT', 'voltage', 250.00, 270.00, 3),
('DEFAULT', 'vibration', 6.00, 12.00, 3);