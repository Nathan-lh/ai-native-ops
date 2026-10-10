package com.aiops.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import java.math.BigDecimal;

@Data
public class TelemetryMessage {

    @JsonProperty("device_code")
    private String deviceCode;

    @JsonProperty("device_type")
    private String deviceType;

    @JsonProperty("temperature")
    private BigDecimal temperature;

    @JsonProperty("humidity")
    private BigDecimal humidity;

    @JsonProperty("current")
    private BigDecimal current;

    @JsonProperty("voltage")
    private BigDecimal voltage;

    @JsonProperty("vibration")
    private BigDecimal vibration;

    @JsonProperty("ts")
    private String ts;
}