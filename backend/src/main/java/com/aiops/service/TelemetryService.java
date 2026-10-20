package com.aiops.service;

import com.aiops.dto.TelemetryMessage;
import com.aiops.entity.Device;
import com.aiops.entity.DeviceLatestStatus;
import com.aiops.entity.Telemetry;
import com.aiops.mapper.DeviceLatestStatusMapper;
import com.aiops.mapper.DeviceMapper;
import com.aiops.mapper.TelemetryMapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class TelemetryService {

    private final HealthEvaluator healthEvaluator;
    private final TelemetryMapper telemetryMapper;
    private final DeviceMapper deviceMapper;
    private final DeviceLatestStatusMapper deviceLatestStatusMapper;
    private final DeviceStatusCacheService deviceStatusCacheService;

    // 遥测验证闭环服务
    private final DeviceRecoveryService deviceRecoveryService;

    // 有界队列：容量 10000，队列满时丢弃以保护数据库（背压）
    private final BlockingQueue<Telemetry> queue = new ArrayBlockingQueue<>(10000);

    private static final int BATCH_SIZE = 100;
    private volatile boolean running = true;

    // 设备编码 -> 设备ID 的本地缓存，避免每次查库
    private final java.util.concurrent.ConcurrentHashMap<String, Long> deviceCache = new java.util.concurrent.ConcurrentHashMap<>();

    // 设备ID -> 设备类型 的本地缓存，避免每条遥测都查一次 device 表
    private final java.util.concurrent.ConcurrentHashMap<Long, String> deviceTypeCache = new java.util.concurrent.ConcurrentHashMap<>();

    public void receiveTelemetry(TelemetryMessage msg) {
        try {
            Telemetry telemetry = convertToEntity(msg);
            // offer 非阻塞，队列满直接丢弃并记录日志
            boolean success = queue.offer(telemetry, 100, TimeUnit.MILLISECONDS);
            if (!success) {
                log.warn("[背压] 队列已满，丢弃一条遥测数据: {}", msg.getDeviceCode());
            }
        } catch (Exception e) {
            log.error("[遥测接收] 异常", e);
        }
    }

    @PostConstruct
    public void startConsumer() {
        Thread consumer = new Thread(() -> {
            List<Telemetry> batch = new ArrayList<>(BATCH_SIZE);
            while (running || !queue.isEmpty()) {
                try {
                    Telemetry first = queue.poll(1, TimeUnit.SECONDS); // 拿第一条
                    if (first != null) {
                        batch.add(first);
                        queue.drainTo(batch, BATCH_SIZE - 1); // 瞬间把剩余凑满一批
                    }
                    if (!batch.isEmpty() && (batch.size() >= BATCH_SIZE || first == null)) {
                        flushBatch(batch);
                        batch.clear();
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                } catch (Exception e) {
                    log.error("[攒批入库] 异常", e);
                }
            }
        }, "telemetry-consumer");
        consumer.setDaemon(true);
        consumer.start();
        log.info("[TelemetryService] 异步攒批消费者已启动...");
    }

    private void flushBatch(List<Telemetry> batch) {
        if (batch.isEmpty()) return;
        long start = System.currentTimeMillis();
        try {
            // 1. 真正的批量插入：一条 SQL 插入整批，大幅减少 DB 往返
            telemetryMapper.batchInsert(batch);

            // 2. 逐条做健康评估 + 更新状态快照
            for (Telemetry t : batch) {
                String deviceType = getDeviceTypeById(t.getDeviceId());
                String status = healthEvaluator.evaluate(t, deviceType);
                updateLatestStatus(t, status);
            }
            log.info("[攒批入库] 成功批量插入 {} 条数据，耗时 {} ms", batch.size(), System.currentTimeMillis() - start);

            // 每批遥测处理后，检测 VERIFYING 工单是否满足恢复条件
            deviceRecoveryService.tryRecover();

        } catch (Exception e) {
            log.error("[攒批入库] 批量插入失败", e);
        }
    }

    private String getDeviceTypeById(Long deviceId) {
        return deviceTypeCache.computeIfAbsent(deviceId, id -> {
            Device d = deviceMapper.selectById(id);
            return d != null ? d.getDeviceType() : "DEFAULT";
        });
    }

    private void updateLatestStatus(Telemetry t, String status) {
        DeviceLatestStatus snapshot = new DeviceLatestStatus();
        snapshot.setDeviceId(t.getDeviceId());
        snapshot.setStatus(status);
        snapshot.setLastSeen(t.getTs());
        snapshot.setLastMetricJson("{}");
        snapshot.setUpdatedAt(LocalDateTime.now());

        // 走缓存服务：先更 DB，再删缓存 + 延迟双删
        deviceStatusCacheService.updateStatus(snapshot);

        // 同步更新设备主表状态（只有当状态变化时才更新，减少写压力）
        if (!"NORMAL".equals(status)) {
            Device device = new Device();
            device.setId(t.getDeviceId());
            device.setStatus(status);
            deviceMapper.updateById(device);
        }
    }

    private Telemetry convertToEntity(TelemetryMessage msg) {
        Telemetry t = new Telemetry();
        Long deviceId = getDeviceIdByCode(msg.getDeviceCode(), msg.getDeviceType());
        t.setDeviceId(deviceId);
        t.setTemperature(msg.getTemperature());
        t.setHumidity(msg.getHumidity());
        t.setCurrent(msg.getCurrent());
        t.setVoltage(msg.getVoltage());
        t.setVibration(msg.getVibration());
        t.setTs(LocalDateTime.parse(msg.getTs(), DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
        return t;
    }

    private Long getDeviceIdByCode(String deviceCode, String deviceType) {
        return deviceCache.computeIfAbsent(deviceCode, code -> {
            Device device = deviceMapper.selectOne(new LambdaQueryWrapper<Device>().eq(Device::getDeviceCode, code));
            if (device == null) {
                device = new Device();
                device.setDeviceCode(code);
                device.setDeviceName(code);
                device.setDeviceType(deviceType);
                device.setStatus("NORMAL");
                deviceMapper.insert(device);
                log.info("[设备注册] 动态注册新设备: {}", code);
            }
            // 顺便缓存 deviceId -> deviceType，避免每条遥测都查 device 表
            deviceTypeCache.put(device.getId(), device.getDeviceType());
            return device.getId();
        });
    }

    @PreDestroy
    public void stop() {
        running = false;
    }
}