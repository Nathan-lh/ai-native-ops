package com.aiops.dto;

import lombok.Data;

@Data
public class AssignOrderRequest {
    private Long repairerId;
    private String reviewComment;
}