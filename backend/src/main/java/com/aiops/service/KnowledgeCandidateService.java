package com.aiops.service;

import com.aiops.entity.Device;
import com.aiops.entity.KnowledgeCandidate;
import com.aiops.entity.RepairOrder;
import com.aiops.mapper.DeviceMapper;
import com.aiops.mapper.KnowledgeCandidateMapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 知识候选 Service
 * 负责：工单完成后生成候选、审核通过/驳回、导出可回流的知识
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class KnowledgeCandidateService {

    private final KnowledgeCandidateMapper candidateMapper;
    private final DeviceMapper deviceMapper;

    /**
     * 工单 COMPLETED 时调用：生成一条知识候选
     * 幂等：同一个工单只生成一次
     */
    @Transactional(rollbackFor = Exception.class)
    public void createFromCompletedOrder(RepairOrder order) {
        if (order == null || order.getId() == null) {
            return;
        }

        // 幂等检查：该工单是否已经生成过候选
        Long exists = candidateMapper.selectCount(
                new LambdaQueryWrapper<KnowledgeCandidate>()
                        .eq(KnowledgeCandidate::getOrderId, order.getId())
        );
        if (exists != null && exists > 0) {
            log.info("[知识回流] 工单 {} 已生成过候选，跳过", order.getId());
            return;
        }

        KnowledgeCandidate c = new KnowledgeCandidate();
        c.setOrderId(order.getId());

        // 从 device 表补 device_type
        if (order.getDeviceId() != null) {
            Device device = deviceMapper.selectById(order.getDeviceId());
            if (device != null) {
                c.setDeviceType(device.getDeviceType());
            }
        }

        // 从工单里拿字段
        c.setFaultPhenomenon(order.getDescription());
        c.setRepairMethod(order.getRepairComment());
        c.setRepairReason(order.getRepairReason());
        // fault_type / telemetry_signature 暂时留空，等人工审核时补充
        c.setSeverity("中");
        c.setStatus("PENDING");
        c.setSubmitTime(LocalDateTime.now());
        c.setSource("工单回流");

        candidateMapper.insert(c);
        log.info("[知识回流] 工单 {} COMPLETED，生成候选 id={}", order.getId(), c.getId());
    }

    /**
     * 分页查询候选列表（可按 status 过滤）
     */
    public Page<KnowledgeCandidate> listPage(String status, int page, int size) {
        Page<KnowledgeCandidate> p = new Page<>(page, size);
        LambdaQueryWrapper<KnowledgeCandidate> qw = new LambdaQueryWrapper<>();
        if (StringUtils.hasText(status)) {
            qw.eq(KnowledgeCandidate::getStatus, status);
        }
        qw.orderByDesc(KnowledgeCandidate::getSubmitTime);
        return candidateMapper.selectPage(p, qw);
    }

    /**
     * 审核通过
     */
    @Transactional(rollbackFor = Exception.class)
    public void approve(Long id, Long reviewerId, String comment) {
        KnowledgeCandidate c = candidateMapper.selectById(id);
        if (c == null) {
            throw new RuntimeException("候选不存在: id=" + id);
        }
        if (!"PENDING".equals(c.getStatus())) {
            throw new RuntimeException("候选状态不是 PENDING，无法审核。当前状态: " + c.getStatus());
        }
        c.setStatus("APPROVED");
        c.setReviewerId(reviewerId);
        c.setReviewComment(comment);
        c.setReviewTime(LocalDateTime.now());
        candidateMapper.updateById(c);
        log.info("[知识回流] 候选 {} 审核通过，审核人 {}", id, reviewerId);
    }

    /**
     * 审核驳回
     */
    @Transactional(rollbackFor = Exception.class)
    public void reject(Long id, Long reviewerId, String comment) {
        KnowledgeCandidate c = candidateMapper.selectById(id);
        if (c == null) {
            throw new RuntimeException("候选不存在: id=" + id);
        }
        if (!"PENDING".equals(c.getStatus())) {
            throw new RuntimeException("候选状态不是 PENDING，无法审核。当前状态: " + c.getStatus());
        }
        c.setStatus("REJECTED");
        c.setReviewerId(reviewerId);
        c.setReviewComment(comment);
        c.setReviewTime(LocalDateTime.now());
        candidateMapper.updateById(c);
        log.info("[知识回流] 候选 {} 审核驳回，审核人 {}", id, reviewerId);
    }

    /**
     * 查询所有已通过审核的候选（供 Python 端回流到知识库用）
     */
    public List<KnowledgeCandidate> listApproved() {
        return candidateMapper.selectList(
                new LambdaQueryWrapper<KnowledgeCandidate>()
                        .eq(KnowledgeCandidate::getStatus, "APPROVED")
                        .orderByAsc(KnowledgeCandidate::getReviewTime)
        );
    }
}