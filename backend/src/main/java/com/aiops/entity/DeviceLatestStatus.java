package com.aiops.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("device_latest_status")
public class DeviceLatestStatus {

    @TableId(value = "device_id", type = IdType.INPUT)
    private Long deviceId;

    private String status;

    private LocalDateTime lastSeen;

    private String lastMetricJson;

    private LocalDateTime updatedAt;
}