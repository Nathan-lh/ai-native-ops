package com.aiops.controller;

import lombok.RequiredArgsConstructor;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * 临时测试 Redisson 分布式锁的接口
 * 生产环境请删除
 */
@RestController
@RequestMapping("/api/test/lock")
@RequiredArgsConstructor
public class LockTestController {

    private final RedissonClient redissonClient;

    @GetMapping
    public Map<String, Object> testLock() throws InterruptedException {
        String lockKey = "test:lock:demo";
        RLock lock = redissonClient.getLock(lockKey);

        Map<String, Object> result = new HashMap<>();
        // tryLock(等待时间, 持有时间, 时间单位)
        boolean acquired = lock.tryLock(0, 10, TimeUnit.SECONDS);
        if (!acquired) {
            result.put("success", false);
            result.put("message", "获取锁失败，说明有其他线程正在执行");
            return result;
        }
        try {
            // 模拟业务处理
            Thread.sleep(3000);
            result.put("success", true);
            result.put("message", "获取锁成功，业务处理完成");
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
        return result;
    }
}