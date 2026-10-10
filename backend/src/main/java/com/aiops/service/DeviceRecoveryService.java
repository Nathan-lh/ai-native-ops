package com.aiops.service;

import com.aiops.entity.Device;
import com.aiops.entity.DeviceLatestStatus;
import com.aiops.entity.FaultRule;
import com.aiops.entity.RepairOrder;
import com.aiops.entity.Telemetry;
import com.aiops.mapper.DeviceLatestStatusMapper;
import com.aiops.mapper.DeviceMapper;
import com.aiops.mapper.FaultRuleMapper;
import com.aiops.mapper.RepairOrderMapper;
import com.aiops.mapper.TelemetryMapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
@RequiredArgsConstructor
public class DeviceRecoveryService {

    private final RepairOrderMapper repairOrderMapper;
    private final TelemetryMapper telemetryMapper;
    private final DeviceMapper deviceMapper;
    private final FaultRuleMapper faultRuleMapper;
    private final DeviceLatestStatusMapper deviceLatestStatusMapper;
    private final KnowledgeCandidateService knowledgeCandidateService;

    /** 连续 N 次遥测正常才恢复 */
    private static final int VERIFY_COUNT = 3;

    /** 节流：距上次扫描至少间隔 5 秒，避免高频扫库 */
    private static final long SCAN_INTERVAL_MS = 5000;
    private final AtomicLong lastScanTime = new AtomicLong(0);

    /**
     * 由 TelemetryService 每批遥测处理后调用
     * 内部做了节流，不用怕每批都调用
     */
    public void tryRecover() {
        long now = System.currentTimeMillis();
        long last = lastScanTime.get();
        if (now - last < SCAN_INTERVAL_MS) return;
        // CAS 保证多线程只有一个能进入扫描
        if (!lastScanTime.compareAndSet(last, now)) return;

        List<RepairOrder> verifyingOrders = repairOrderMapper.selectList(
                new LambdaQueryWrapper<RepairOrder>().eq(RepairOrder::getStatus, "VERIFYING"));
        if (verifyingOrders.isEmpty()) return;

        for (RepairOrder order : verifyingOrders) {
            try {
                checkAndRecover(order);
            } catch (Exception e) {
                log.error("[闭环] 处理工单 {} 异常", order.getId(), e);
            }
        }
    }

    private void checkAndRecover(RepairOrder order) {
        Long deviceId = order.getDeviceId();

        // 1. 拿最近 N 条遥测（按时间倒序）
        List<Telemetry> recent = telemetryMapper.selectList(
                new LambdaQueryWrapper<Telemetry>()
                        .eq(Telemetry::getDeviceId, deviceId)
                        .orderByDesc(Telemetry::getTs)
                        .last("LIMIT " + VERIFY_COUNT));
        if (recent.size() < VERIFY_COUNT) return;

        // 2. 拿设备类型对应的规则
        Device device = deviceMapper.selectById(deviceId);
        if (device == null) return;
        List<FaultRule> rules = getRules(device.getDeviceType());
        if (rules.isEmpty()) return;

        // 3. 逐条检查，只要有一条不正常就直接放弃（等待下次扫描）
        for (Telemetry t : recent) {
            if (!isAllNormal(t, rules)) {
                return;
            }
        }

        // 4. 都正常 → 执行恢复
        doRecover(order, deviceId);
    }

    private List<FaultRule> getRules(String deviceType) {
        List<FaultRule> rules = faultRuleMapper.selectList(
                new LambdaQueryWrapper<FaultRule>().eq(FaultRule::getDeviceType, deviceType));
        if (rules.isEmpty()) {
            rules = faultRuleMapper.selectList(
                    new LambdaQueryWrapper<FaultRule>().eq(FaultRule::getDeviceType, "DEFAULT"));
        }
        return rules;
    }

    private boolean isAllNormal(Telemetry t, List<FaultRule> rules) {
        for (FaultRule rule : rules) {
            BigDecimal value = getMetricValue(t, rule.getMetric());
            if (value == null) continue;
            if (value.compareTo(rule.getWarnThreshold()) > 0) {
                return false;
            }
        }
        return true;
    }

    private BigDecimal getMetricValue(Telemetry t, String metric) {
        return switch (metric) {
            case "temperature" -> t.getTemperature();
            case "humidity" -> t.getHumidity();
            case "current" -> t.getCurrent();
            case "voltage" -> t.getVoltage();
            case "vibration" -> t.getVibration();
            default -> null;
        };
    }

    /**
     * 真正的恢复：工单 → COMPLETED，设备 → NORMAL
     * 用乐观锁 version 防止与管理员手动验证并发冲突
     * 自动完成时也生成知识候选（知识回流）
     */
    @Transactional(rollbackFor = Exception.class)
    public void doRecover(RepairOrder order, Long deviceId) {
        RepairOrder update = new RepairOrder();
        update.setId(order.getId());
        update.setVersion(order.getVersion());
        update.setStatus("COMPLETED");
        update.setCompleteTime(LocalDateTime.now());
        int rows = repairOrderMapper.updateById(update);
        if (rows == 0) {
            log.warn("[闭环] 工单 {} 更新失败（乐观锁冲突或已被人处理）", order.getId());
            return;
        }

        // 设备表状态恢复正常
        Device d = new Device();
        d.setId(deviceId);
        d.setStatus("NORMAL");
        deviceMapper.updateById(d);

        // 快照表状态也恢复正常
        DeviceLatestStatus snap = deviceLatestStatusMapper.selectById(deviceId);
        if (snap != null) {
            snap.setStatus("NORMAL");
            snap.setUpdatedAt(LocalDateTime.now());
            deviceLatestStatusMapper.updateById(snap);
        }

        // 自动完成时生成知识候选
        // 重新查一次拿最新的 COMPLETED 数据（repairComment / repairReason 已在上一步写入）
        try {
            RepairOrder fresh = repairOrderMapper.selectById(order.getId());
            if (fresh != null) {
                knowledgeCandidateService.createFromCompletedOrder(fresh);
            }
        } catch (Exception e) {
            log.error("[知识回流] 工单 {} 自动完成时生成候选失败", order.getId(), e);
        }

        log.info("[闭环] 设备 {} 遥测连续 {} 次正常，工单 {} 自动完成，设备状态恢复 NORMAL",
                deviceId, VERIFY_COUNT, order.getId());
    }
}