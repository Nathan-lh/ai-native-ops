package com.aiops.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;

@Data
@TableName("fault_rule")
public class FaultRule {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String deviceType;

    private String metric;

    private BigDecimal warnThreshold;

    private BigDecimal faultThreshold;

    private Integer consecutiveCount;
}