package com.aiops.service;

import com.aiops.dto.AssignOrderRequest;
import com.aiops.dto.CompleteOrderRequest;
import com.aiops.dto.CreateOrderRequest;
import com.aiops.entity.Device;
import com.aiops.entity.DeviceLatestStatus;
import com.aiops.entity.RepairOrder;
import com.aiops.mapper.DeviceLatestStatusMapper;
import com.aiops.mapper.DeviceMapper;
import com.aiops.mapper.RepairOrderMapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class RepairOrderService {

    private final RepairOrderMapper repairOrderMapper;
    private final KnowledgeCandidateService knowledgeCandidateService;
    private final RedissonClient redissonClient;
    private final PlatformTransactionManager transactionManager;
    private final DeviceMapper deviceMapper;
    private final DeviceLatestStatusMapper deviceLatestStatusMapper;
    private final StringRedisTemplate redis;

    // ==================== 创建工单 ====================
    @Transactional(rollbackFor = Exception.class)
    public RepairOrder createOrder(CreateOrderRequest req, Long reporterId) {
        RepairOrder order = new RepairOrder();
        order.setDeviceId(req.getDeviceId());
        order.setReporterId(reporterId);
        order.setDescription(req.getDescription());
        order.setAiDiagnosisSummary(req.getAiDiagnosisSummary());
        order.setStatus("PENDING_REVIEW");
        order.setVersion(0);
        repairOrderMapper.insert(order);
        log.info("[工单] 创建成功 id={}, deviceId={}, reporterId={}", order.getId(), req.getDeviceId(), reporterId);
        return order;
    }

    // ==================== 派单（Redisson 分布式锁 + 三道防线） ====================
    /**
     * 三道防线：
     *   1. Redisson 分布式锁（防止多实例并发抢同一工单）
     *   2. 状态前置校验（防止非法状态跳转）
     *   3. 乐观锁 version（防跨实例竞争的最后兜底）
     *
     * 关键：锁必须在事务外面，用 TransactionTemplate 手动管理事务
     */
    public boolean assignOrder(Long orderId, AssignOrderRequest req, Long reviewerId) {
        String lockKey = "lock:order:assign:" + orderId;
        RLock lock = redissonClient.getLock(lockKey);

        try {
            if (!lock.tryLock(3, 10, TimeUnit.SECONDS)) {
                log.warn("[工单] 派单获取锁失败，orderId={}", orderId);
                throw new RuntimeException("系统繁忙，请稍后重试");
            }
            try {
                TransactionTemplate template = new TransactionTemplate(transactionManager);
                return Boolean.TRUE.equals(template.execute(status -> doAssign(orderId, req, reviewerId)));
            } finally {
                if (lock.isHeldByCurrentThread()) {
                    lock.unlock();
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("获取锁被中断");
        }
    }

    private boolean doAssign(Long orderId, AssignOrderRequest req, Long reviewerId) {
        RepairOrder order = repairOrderMapper.selectById(orderId);
        if (order == null) throw new RuntimeException("工单不存在");

        if (!"PENDING_REVIEW".equals(order.getStatus())) {
            throw new RuntimeException("当前状态不允许派单，当前状态：" + order.getStatus());
        }

        order.setStatus("ASSIGNED");
        order.setReviewerId(reviewerId);
        order.setReviewComment(req.getReviewComment());
        order.setRepairerId(req.getRepairerId());
        order.setReviewTime(LocalDateTime.now());

        int rows = repairOrderMapper.updateById(order);
        if (rows == 0) {
            log.warn("[工单] 派单失败，乐观锁冲突，orderId={}", orderId);
            throw new RuntimeException("工单已被其他人处理，请刷新重试");
        }
        log.info("[工单] 派单成功 id={}, repairerId={}", orderId, req.getRepairerId());
        return true;
    }

    // ==================== 驳回 ====================
    @Transactional(rollbackFor = Exception.class)
    public boolean rejectOrder(Long orderId, String reviewComment, Long reviewerId) {
        RepairOrder order = repairOrderMapper.selectById(orderId);
        if (order == null) throw new RuntimeException("工单不存在");
        if (!"PENDING_REVIEW".equals(order.getStatus())) {
            throw new RuntimeException("当前状态不允许驳回");
        }

        order.setStatus("REJECTED");
        order.setReviewerId(reviewerId);
        order.setReviewComment(reviewComment);
        order.setReviewTime(LocalDateTime.now());

        int rows = repairOrderMapper.updateById(order);
        if (rows == 0) throw new RuntimeException("工单已被其他人处理");
        return true;
    }

    // ==================== 接单 ====================
    @Transactional(rollbackFor = Exception.class)
    public boolean startRepair(Long orderId, Long repairerId) {
        RepairOrder order = repairOrderMapper.selectById(orderId);
        if (order == null) throw new RuntimeException("工单不存在");
        if (!"ASSIGNED".equals(order.getStatus())) {
            throw new RuntimeException("当前状态不允许接单");
        }
        if (!repairerId.equals(order.getRepairerId())) {
            throw new RuntimeException("您不是该工单的指派维修工");
        }

        order.setStatus("REPAIRING");
        int rows = repairOrderMapper.updateById(order);
        if (rows == 0) throw new RuntimeException("工单已被其他人操作");
        log.info("[工单] 接单成功 id={}, repairerId={}", orderId, repairerId);
        return true;
    }

    // ==================== 完成维修 ====================
    @Transactional(rollbackFor = Exception.class)
    public boolean completeRepair(Long orderId, CompleteOrderRequest req, Long repairerId) {
        RepairOrder order = repairOrderMapper.selectById(orderId);
        if (order == null) throw new RuntimeException("工单不存在");
        if (!"REPAIRING".equals(order.getStatus())) {
            throw new RuntimeException("当前状态不允许完成维修");
        }
        if (!repairerId.equals(order.getRepairerId())) {
            throw new RuntimeException("您不是该工单的指派维修工");
        }

        order.setStatus("VERIFYING");
        order.setRepairComment(req.getRepairComment());
        order.setRepairReason(req.getRepairReason());
        order.setCompleteTime(LocalDateTime.now());

        int rows = repairOrderMapper.updateById(order);
        if (rows == 0) throw new RuntimeException("工单已被其他人操作");
        log.info("[工单] 维修完成，进入待验证 id={}", orderId);
        return true;
    }

    // ==================== 验证通过（含设备状态恢复 + 缓存清理 + 知识回流） ====================
    /**
     * 验证通过：VERIFYING → COMPLETED
     * 完成后：
     *   1. 恢复设备状态为 NORMAL
     *   2. 更新快照表
     *   3. 删除 Redis 缓存（延迟双删）
     *   4. 生成知识候选（知识回流）
     */
    @Transactional(rollbackFor = Exception.class)
    public boolean verifyPass(Long orderId) {
        RepairOrder order = repairOrderMapper.selectById(orderId);
        if (order == null) throw new RuntimeException("工单不存在");
        if (!"VERIFYING".equals(order.getStatus())) {
            throw new RuntimeException("当前状态不允许验证通过");
        }

        // 1. 工单状态 → COMPLETED
        order.setStatus("COMPLETED");
        int rows = repairOrderMapper.updateById(order);
        if (rows == 0) throw new RuntimeException("工单已被其他人操作");

        // 2. 恢复设备状态为 NORMAL
        Long deviceId = order.getDeviceId();
        if (deviceId != null) {
            Device d = new Device();
            d.setId(deviceId);
            d.setStatus("NORMAL");
            deviceMapper.updateById(d);

            // 2.1 快照表也恢复
            DeviceLatestStatus snap = deviceLatestStatusMapper.selectById(deviceId);
            if (snap != null) {
                snap.setStatus("NORMAL");
                snap.setUpdatedAt(LocalDateTime.now());
                deviceLatestStatusMapper.updateById(snap);
            }

            // 2.2 删除 Redis 缓存（先更 DB 再删缓存 + 延迟双删）
            String cacheKey = "device:status:" + deviceId;
            redis.delete(cacheKey);
            try {
                Thread.sleep(100);
                redis.delete(cacheKey);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }

            log.info("[工单] 验证通过后设备 {} 状态已恢复 NORMAL，缓存已清理", deviceId);
        }

        // 3. 知识回流
        try {
            knowledgeCandidateService.createFromCompletedOrder(order);
        } catch (Exception e) {
            log.error("[知识回流] 工单 {} 生成候选失败", orderId, e);
        }

        log.info("[工单] 验证通过，工单完成 id={}", orderId);
        return true;
    }

    // ==================== 查询工单列表（按角色过滤） ====================
    /**
     * - STUDENT / TEACHER：只看自己创建的
     * - REPAIRER：只看派给自己的
     * - ADMIN：看全部
     */
    public List<RepairOrder> listOrders(String status, Long userId, String role) {
        LambdaQueryWrapper<RepairOrder> wrapper = new LambdaQueryWrapper<>();

        if (status != null && !status.isEmpty()) {
            wrapper.eq(RepairOrder::getStatus, status);
        }

        if ("STUDENT".equals(role) || "TEACHER".equals(role)) {
            wrapper.eq(RepairOrder::getReporterId, userId);
        } else if ("REPAIRER".equals(role)) {
            wrapper.eq(RepairOrder::getRepairerId, userId);
        }
        // ADMIN 不加条件

        wrapper.orderByDesc(RepairOrder::getCreateTime);
        return repairOrderMapper.selectList(wrapper);
    }

    // ==================== 查询工单详情 ====================
    public RepairOrder getOrder(Long orderId) {
        return repairOrderMapper.selectById(orderId);
    }
}