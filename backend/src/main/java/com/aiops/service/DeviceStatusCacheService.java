package com.aiops.service;

import com.aiops.entity.DeviceLatestStatus;
import com.aiops.mapper.DeviceLatestStatusMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * 设备最新状态缓存 Service
 * 实现 Cache-Aside 模式：
 *   读：先查 Redis → 未命中查 MySQL → 回填 Redis
 *   写：先更 DB → 删缓存 → 延迟 500ms 再删一次（延迟双删）
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DeviceStatusCacheService {

    private final StringRedisTemplate redis;
    private final DeviceLatestStatusMapper statusMapper;

    /** Redis key 前缀 */
    private static final String KEY_PREFIX = "device:status:";

    /** 缓存过期时间（秒），防止缓存永久脏 */
    private static final long CACHE_TTL_SECONDS = 300;

    /** 延迟双删的延迟时间（毫秒） */
    private static final long DOUBLE_DELETE_DELAY_MS = 500;

    /** 延迟双删用的调度器 */
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);

    /**
     * 读缓存（Cache-Aside）
     * 1. 先查 Redis Hash
     * 2. 未命中 → 查 MySQL
     * 3. 回填 Redis，设置 TTL
     */
    public Map<String, Object> getLatestStatus(Long deviceId) {
        String key = KEY_PREFIX + deviceId;

        // 1. 查 Redis
        Map<Object, Object> cached = redis.opsForHash().entries(key);
        if (!cached.isEmpty()) {
            log.info("[缓存] 命中 key={}", key);
            Map<String, Object> result = new HashMap<>();
            cached.forEach((k, v) -> result.put(k.toString(), v));
            return result;
        }

        // 2. 未命中 → 查 MySQL
        log.info("[缓存] 未命中 key={}，回源 MySQL", key);
        DeviceLatestStatus snapshot = statusMapper.selectById(deviceId);
        if (snapshot == null) {
            return null;
        }

        // 3. 回填 Redis
        Map<String, Object> result = toMap(snapshot);
        Map<String, String> stringMap = new HashMap<>();
        result.forEach((k, v) -> stringMap.put(k, v == null ? "" : v.toString()));
        redis.opsForHash().putAll(key, stringMap);
        redis.expire(key, CACHE_TTL_SECONDS, TimeUnit.SECONDS);
        log.info("[缓存] 已回填 key={}，TTL={}s", key, CACHE_TTL_SECONDS);

        return result;
    }

    /**
     * 写缓存（先更 DB 再删缓存 + 延迟双删）
     * 1. 先更新 MySQL（保证 DB 是权威数据源）
     * 2. 删除 Redis 缓存
     * 3. 延迟 500ms 再删一次，防止"删缓存→并发读回填旧值"
     */
    public void updateStatus(DeviceLatestStatus snapshot) {
        Long deviceId = snapshot.getDeviceId();
        String key = KEY_PREFIX + deviceId;

        // 1. 先更新 MySQL
        if (statusMapper.selectById(deviceId) == null) {
            statusMapper.insert(snapshot);
        } else {
            statusMapper.updateById(snapshot);
        }
        log.info("[缓存] DB 更新完成 deviceId={}", deviceId);

        // 2. 删除 Redis（第一次删）
        redis.delete(key);
        log.info("[缓存] 第一次删除 key={}", key);

        // 3. 延迟 500ms 再删一次（延迟双删）
        scheduler.schedule(() -> {
            try {
                redis.delete(key);
                log.info("[缓存] 延迟双删完成 key={}", key);
            } catch (Exception e) {
                log.error("[缓存] 延迟双删异常 key={}", key, e);
            }
        }, DOUBLE_DELETE_DELAY_MS, TimeUnit.MILLISECONDS);
    }

    /**
     * 实体 → Map（用于写 Redis Hash）
     */
    private Map<String, Object> toMap(DeviceLatestStatus s) {
        Map<String, Object> m = new HashMap<>();
        m.put("deviceId", s.getDeviceId());
        m.put("status", s.getStatus());
        m.put("lastSeen", s.getLastSeen() != null ? s.getLastSeen().toString() : "");
        m.put("lastMetricJson", s.getLastMetricJson() == null ? "" : s.getLastMetricJson());
        m.put("updatedAt", s.getUpdatedAt() != null ? s.getUpdatedAt().toString() : "");
        return m;
    }
}