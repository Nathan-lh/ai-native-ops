package com.aiops.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 知识候选（待审核回流知识库）
 */
@Data
@TableName("knowledge_candidate")
public class KnowledgeCandidate {

    @TableId(type = IdType.AUTO)
    private Long id;

    /** 来源工单ID */
    private Long orderId;

    /** 设备类型 */
    private String deviceType;

    /** 故障类型 */
    private String faultType;

    /** 故障现象 */
    private String faultPhenomenon;

    /** 遥测签名 */
    private String telemetrySignature;

    /** 可能原因（JSON 数组字符串） */
    private String possibleCauses;

    /** 排查步骤（JSON 数组字符串） */
    private String troubleshootSteps;

    /** 处理方法 */
    private String repairMethod;

    /** 维修真实原因（工单回填） */
    private String repairReason;

    /** 严重程度 */
    private String severity;

    /** PENDING / APPROVED / REJECTED */
    private String status;

    /** 审核人ID */
    private Long reviewerId;

    /** 审核意见 */
    private String reviewComment;

    /** 提交时间 */
    private LocalDateTime submitTime;

    /** 审核时间 */
    private LocalDateTime reviewTime;

    /** 来源 */
    private String source;
}