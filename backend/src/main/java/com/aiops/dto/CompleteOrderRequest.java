package com.aiops.dto;

import lombok.Data;

@Data
public class CompleteOrderRequest {
    private String repairComment;
    private String repairReason;
}