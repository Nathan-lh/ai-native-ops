package com.aiops.controller;

import com.aiops.entity.DeviceLatestStatus;
import com.aiops.service.DeviceStatusCacheService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 设备状态缓存查询接口（用于验证缓存一致性）
 */
@RestController
@RequestMapping("/api/device/cache")
@RequiredArgsConstructor
public class DeviceCacheController {

    private final DeviceStatusCacheService cacheService;

    /**
     * GET /api/device/cache/{deviceId}
     */
    @GetMapping("/{deviceId}")
    public ResponseEntity<?> get(@PathVariable Long deviceId) {
        Map<String, Object> data = cacheService.getLatestStatus(deviceId);
        if (data == null) {
            return ResponseEntity.status(404).body(Map.of("message", "设备状态不存在"));
        }
        return ResponseEntity.ok(data);
    }

    /**
     * POST /api/test/cache-write/{deviceId}
     * 测试用：改一次状态，走"先更 DB 再删缓存 + 延迟双删"
     * Body: {"status": "FAULT"}
     */
    @PostMapping("/{deviceId}/test-write")
    public ResponseEntity<?> testWrite(@PathVariable Long deviceId,
                                       @RequestBody Map<String, String> body) {
        String newStatus = body.getOrDefault("status", "NORMAL");
        DeviceLatestStatus snapshot = new DeviceLatestStatus();
        snapshot.setDeviceId(deviceId);
        snapshot.setStatus(newStatus);
        snapshot.setLastSeen(LocalDateTime.now());
        snapshot.setLastMetricJson("{\"test\":true}");
        snapshot.setUpdatedAt(LocalDateTime.now());
        cacheService.updateStatus(snapshot);
        return ResponseEntity.ok(Map.of("message", "写入完成", "newStatus", newStatus));
    }
}