package com.aiops.service;

import com.aiops.entity.FaultRule;
import com.aiops.entity.Telemetry;
import com.aiops.mapper.FaultRuleMapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
@RequiredArgsConstructor
public class HealthEvaluator {

    private final FaultRuleMapper faultRuleMapper;

    // 缓存规则，避免每次都查库
    private final Map<String, List<FaultRule>> ruleCache = new ConcurrentHashMap<>();

    // 去抖计数器：key = deviceId + ":" + metric，value = 连续异常次数
    private final Map<String, Integer> warningCounter = new ConcurrentHashMap<>();
    private final Map<String, Integer> faultCounter = new ConcurrentHashMap<>();

    /**
     * 对一条遥测数据进行健康评估
     * @return 评估后的设备状态：NORMAL / WARNING / FAULT
     */
    public String evaluate(Telemetry t, String deviceType) {
        List<FaultRule> rules = getRules(deviceType);
        String finalStatus = "NORMAL";

        for (FaultRule rule : rules) {
            BigDecimal value = getMetricValue(t, rule.getMetric());
            if (value == null) continue;

            String key = t.getDeviceId() + ":" + rule.getMetric();
            int warnCount = rule.getConsecutiveCount() == null ? 3 : rule.getConsecutiveCount();
            int faultCount = rule.getConsecutiveCount() == null ? 3 : rule.getConsecutiveCount();

            // 判断是否超过“故障”阈值
            if (value.compareTo(rule.getFaultThreshold()) > 0) {
                int count = faultCounter.merge(key, 1, Integer::sum);
                warningCounter.put(key, 0); // 重置预警计数
                if (count >= faultCount) {
                    finalStatus = "FAULT";
                    log.warn("[健康评估] 设备 {} 指标 {} 连续 {} 次超过故障阈值 {}，当前值 {}",
                            t.getDeviceId(), rule.getMetric(), count, rule.getFaultThreshold(), value);
                }
            }
            // 判断是否超过“预警”阈值
            else if (value.compareTo(rule.getWarnThreshold()) > 0) {
                int count = warningCounter.merge(key, 1, Integer::sum);
                faultCounter.put(key, 0); // 重置故障计数
                if (count >= warnCount && finalStatus.equals("NORMAL")) {
                    finalStatus = "WARNING";
                    log.info("[健康评估] 设备 {} 指标 {} 连续 {} 次超过预警阈值 {}，当前值 {}",
                            t.getDeviceId(), rule.getMetric(), count, rule.getWarnThreshold(), value);
                }
            }
            // 正常，重置计数
            else {
                warningCounter.put(key, 0);
                faultCounter.put(key, 0);
            }
        }
        return finalStatus;
    }

    /**
     * 获取指定设备类型的规则，如果没有则返回 DEFAULT
     */
    private List<FaultRule> getRules(String deviceType) {
        return ruleCache.computeIfAbsent(deviceType, type -> {
            List<FaultRule> rules = faultRuleMapper.selectList(
                    new LambdaQueryWrapper<FaultRule>().eq(FaultRule::getDeviceType, type));
            if (rules.isEmpty()) {
                rules = faultRuleMapper.selectList(
                        new LambdaQueryWrapper<FaultRule>().eq(FaultRule::getDeviceType, "DEFAULT"));
            }
            log.info("[健康评估] 加载设备类型 {} 的规则 {} 条", type, rules.size());
            return rules;
        });
    }

    /**
     * 根据指标名从遥测实体中取出对应的值
     */
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
}