package com.aiops.dto;

import lombok.Data;

@Data
public class CreateOrderRequest {
    private Long deviceId;
    private String description;
    private String aiDiagnosisSummary;
}