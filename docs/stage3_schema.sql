-- 工单系统相关表
USE ai_ops;

-- 用户表
CREATE TABLE IF NOT EXISTS sys_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(100) NOT NULL COMMENT '密码(BCrypt加密)',
    real_name VARCHAR(50) COMMENT '真实姓名',
    phone VARCHAR(20) COMMENT '手机号',
    role VARCHAR(20) NOT NULL DEFAULT 'STUDENT' COMMENT '角色:STUDENT/TEACHER/ADMIN/REPAIRER',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='用户表';

-- 工单表（核心状态机）
CREATE TABLE IF NOT EXISTS repair_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id BIGINT NOT NULL COMMENT '设备ID',
    reporter_id BIGINT NOT NULL COMMENT '报修人ID',
    description VARCHAR(1000) COMMENT '故障描述',
    ai_diagnosis_summary TEXT COMMENT 'AI诊断摘要',
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING_REVIEW' COMMENT '状态:PENDING_REVIEW/ASSIGNED/REPAIRING/VERIFYING/COMPLETED/REJECTED',
    reviewer_id BIGINT COMMENT '审核人ID',
    review_comment VARCHAR(500) COMMENT '审核意见',
    repairer_id BIGINT COMMENT '维修工ID',
    repair_comment VARCHAR(500) COMMENT '维修备注',
    repair_reason TEXT COMMENT '真实原因(回流知识库用)',
    review_time DATETIME COMMENT '审核时间',
    complete_time DATETIME COMMENT '完成时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_device_id (device_id),
    KEY idx_status (status)
) COMMENT='工单表';