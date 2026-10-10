package com.aiops.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("telemetry")
public class Telemetry {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long deviceId;

    private BigDecimal temperature;

    private BigDecimal humidity;

    // 注意：current 是 SQL 保留字，必须用反引号包裹
    @TableField("`current`")
    private BigDecimal current;

    private BigDecimal voltage;

    private BigDecimal vibration;

    private LocalDateTime ts;
}