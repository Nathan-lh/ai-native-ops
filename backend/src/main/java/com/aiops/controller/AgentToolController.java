package com.aiops.controller;

import com.aiops.entity.Device;
import com.aiops.entity.DeviceLatestStatus;
import com.aiops.entity.RepairOrder;
import com.aiops.entity.Telemetry;
import com.aiops.mapper.DeviceLatestStatusMapper;
import com.aiops.mapper.DeviceMapper;
import com.aiops.mapper.RepairOrderMapper;
import com.aiops.mapper.TelemetryMapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

@RestController
@RequestMapping("/api/agent/tools")
@RequiredArgsConstructor
public class AgentToolController {

    private final DeviceMapper deviceMapper;
    private final DeviceLatestStatusMapper deviceLatestStatusMapper;
    private final TelemetryMapper telemetryMapper;
    private final RepairOrderMapper repairOrderMapper;

    /**
     * 查设备列表
     * 返回：total（符合条件总数）、returned（本次返回数）、truncated（是否被截断）、devices
     */
    @GetMapping("/devices")
    public ResponseEntity<?> listDevices(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String deviceType,
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "200") Integer limit) {

        Supplier<LambdaQueryWrapper<Device>> buildWrapper = () -> {
            LambdaQueryWrapper<Device> w = new LambdaQueryWrapper<>();
            if (status != null && !status.isEmpty()) w.eq(Device::getStatus, status);
            if (deviceType != null && !deviceType.isEmpty()) w.eq(Device::getDeviceType, deviceType);
            if (keyword != null && !keyword.isEmpty()) {
                w.and(x -> x.like(Device::getDeviceName, keyword).or().like(Device::getDeviceCode, keyword));
            }
            return w;
        };

        Long total = deviceMapper.selectCount(buildWrapper.get());
        LambdaQueryWrapper<Device> pageWrapper = buildWrapper.get();
        pageWrapper.last("LIMIT " + Math.min(limit, 500));
        List<Device> devices = deviceMapper.selectList(pageWrapper);

        Map<String, Object> result = new HashMap<>();
        result.put("total", total);
        result.put("returned", devices.size());
        result.put("truncated", total > devices.size());
        result.put("devices", devices);
        return ResponseEntity.ok(result);
    }

    /**
     * 查某台设备的实时状态（含最新遥测）
     */
    @GetMapping("/device-status")
    public ResponseEntity<?> getDeviceStatus(@RequestParam Long deviceId) {
        Device device = deviceMapper.selectById(deviceId);
        if (device == null) {
            return ResponseEntity.status(404).body(Map.of("message", "设备不存在: id=" + deviceId));
        }
        DeviceLatestStatus snapshot = deviceLatestStatusMapper.selectById(deviceId);
        List<Telemetry> recent = telemetryMapper.selectList(
                new LambdaQueryWrapper<Telemetry>()
                        .eq(Telemetry::getDeviceId, deviceId)
                        .orderByDesc(Telemetry::getTs)
                        .last("LIMIT 1"));
        Telemetry latest = recent.isEmpty() ? null : recent.get(0);

        Map<String, Object> result = new HashMap<>();
        result.put("device", device);
        result.put("currentStatus", device.getStatus());
        result.put("lastSeen", snapshot != null ? snapshot.getLastSeen() : null);
        result.put("latestTelemetry", latest);
        return ResponseEntity.ok(result);
    }

    /**
     * 查某台设备的遥测趋势（最近 N 条）
     */
    @GetMapping("/telemetry")
    public ResponseEntity<?> getTelemetry(
            @RequestParam Long deviceId,
            @RequestParam(defaultValue = "50") Integer limit) {

        // 该设备的总遥测条数
        Long total = telemetryMapper.selectCount(
                new LambdaQueryWrapper<Telemetry>().eq(Telemetry::getDeviceId, deviceId));

        List<Telemetry> list = telemetryMapper.selectList(
                new LambdaQueryWrapper<Telemetry>()
                        .eq(Telemetry::getDeviceId, deviceId)
                        .orderByDesc(Telemetry::getTs)
                        .last("LIMIT " + Math.min(limit, 200)));

        Map<String, Object> result = new HashMap<>();
        result.put("deviceId", deviceId);
        result.put("total", total);
        result.put("returned", list.size());
        result.put("truncated", total > list.size());
        result.put("telemetryList", list);
        return ResponseEntity.ok(result);
    }

    /**
     * 查工单列表
     */
    @GetMapping("/orders")
    public ResponseEntity<?> listOrders(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) Long deviceId,
            @RequestParam(defaultValue = "100") Integer limit) {

        Supplier<LambdaQueryWrapper<RepairOrder>> buildWrapper = () -> {
            LambdaQueryWrapper<RepairOrder> w = new LambdaQueryWrapper<>();
            if (status != null && !status.isEmpty()) w.eq(RepairOrder::getStatus, status);
            if (deviceId != null) w.eq(RepairOrder::getDeviceId, deviceId);
            return w;
        };

        Long total = repairOrderMapper.selectCount(buildWrapper.get());
        LambdaQueryWrapper<RepairOrder> pageWrapper = buildWrapper.get();
        pageWrapper.orderByDesc(RepairOrder::getCreateTime);
        pageWrapper.last("LIMIT " + Math.min(limit, 300));
        List<RepairOrder> orders = repairOrderMapper.selectList(pageWrapper);

        Map<String, Object> result = new HashMap<>();
        result.put("total", total);
        result.put("returned", orders.size());
        result.put("truncated", total > orders.size());
        result.put("orders", orders);
        return ResponseEntity.ok(result);
    }

    /**
     * 设备总览统计：总数、按状态、按类型、按"状态×类型"交叉统计
     */
    @GetMapping("/device-summary")
    public ResponseEntity<?> deviceSummary() {
        // 1. 按状态分组
        com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<Device> w1 =
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<>();
        w1.select("status", "COUNT(*) as cnt").groupBy("status");
        List<Map<String, Object>> statusRows = deviceMapper.selectMaps(w1);

        // 2. 按类型分组
        com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<Device> w2 =
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<>();
        w2.select("device_type", "COUNT(*) as cnt").groupBy("device_type");
        List<Map<String, Object>> typeRows = deviceMapper.selectMaps(w2);

        // 3. 按"状态 × 类型"交叉分组
        com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<Device> w3 =
                new com.baomidou.mybatisplus.core.conditions.query.QueryWrapper<>();
        w3.select("status", "device_type", "COUNT(*) as cnt")
                .groupBy("status", "device_type");
        List<Map<String, Object>> crossRows = deviceMapper.selectMaps(w3);

        Map<String, Object> byStatus = new HashMap<>();
        long total = 0;
        for (Map<String, Object> row : statusRows) {
            long c = ((Number) row.get("cnt")).longValue();
            byStatus.put(String.valueOf(row.get("status")), c);
            total += c;
        }

        Map<String, Object> byType = new HashMap<>();
        for (Map<String, Object> row : typeRows) {
            byType.put(String.valueOf(row.get("device_type")),
                    ((Number) row.get("cnt")).longValue());
        }

        // 交叉统计结构：{"WARNING": {"空调": 4, "电机": 4, ...}, "FAULT": {...}}
        Map<String, Map<String, Long>> cross = new HashMap<>();
        for (Map<String, Object> row : crossRows) {
            String status = String.valueOf(row.get("status"));
            String type = String.valueOf(row.get("device_type"));
            long c = ((Number) row.get("cnt")).longValue();
            cross.computeIfAbsent(status, k -> new HashMap<>()).put(type, c);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("total", total);
        result.put("byStatus", byStatus);
        result.put("byType", byType);
        result.put("byStatusAndType", cross);
        return ResponseEntity.ok(result);
    }

    @GetMapping("/ping")
    public ResponseEntity<?> ping() {
        return ResponseEntity.ok(Map.of("status", "UP", "service", "java-backend-tools"));
    }
}