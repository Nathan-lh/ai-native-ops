package com.aiops.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.Version;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("repair_order")
public class RepairOrder {

    @TableId(type = IdType.AUTO)
    private Long id;

    @Version
    private Integer version;

    private Long deviceId;

    private Long reporterId;

    private String description;

    private String aiDiagnosisSummary;

    private String status;

    private Long reviewerId;

    private String reviewComment;

    private Long repairerId;

    private String repairComment;

    private String repairReason;

    private LocalDateTime reviewTime;

    private LocalDateTime completeTime;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}