package com.aiops.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * 健康检查接口
 */
@RestController
public class HealthController {

    /**
     * GET /api/health
     */
    @GetMapping("/api/health")
    public Map<String, Object> health() {
        Map<String, Object> result = new HashMap<>();
        result.put("status", "UP");                              // 状态：运行中
        result.put("service", "ai-ops-backend");                 // 服务名
        result.put("time", LocalDateTime.now().toString());      // 当前时间
        return result;
    }
}
