package com.aiops.controller;

import com.aiops.dto.AssignOrderRequest;
import com.aiops.dto.CompleteOrderRequest;
import com.aiops.dto.CreateOrderRequest;
import com.aiops.entity.RepairOrder;
import com.aiops.service.RepairOrderService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
public class RepairOrderController {

    private final RepairOrderService repairOrderService;

    /** 创建工单（学生/老师） */
    @PostMapping
    public ResponseEntity<?> create(@RequestBody CreateOrderRequest req, HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        RepairOrder order = repairOrderService.createOrder(req, userId);
        return ResponseEntity.ok(order);
    }

    /** 审核派单（管理员） */
    @PostMapping("/{id}/assign")
    public ResponseEntity<?> assign(@PathVariable Long id,
                                    @RequestBody AssignOrderRequest req,
                                    HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        String role = (String) request.getAttribute("role");
        if (!"ADMIN".equals(role)) {
            return ResponseEntity.status(403).body(Map.of("message", "只有管理员可以派单"));
        }
        try {
            repairOrderService.assignOrder(id, req, userId);
            return ResponseEntity.ok(Map.of("message", "派单成功"));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("message", e.getMessage()));
        }
    }

    /** 驳回（管理员） */
    @PostMapping("/{id}/reject")
    public ResponseEntity<?> reject(@PathVariable Long id,
                                    @RequestBody Map<String, String> body,
                                    HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        String role = (String) request.getAttribute("role");
        if (!"ADMIN".equals(role)) {
            return ResponseEntity.status(403).body(Map.of("message", "只有管理员可以驳回"));
        }
        try {
            repairOrderService.rejectOrder(id, body.get("reviewComment"), userId);
            return ResponseEntity.ok(Map.of("message", "驳回成功"));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("message", e.getMessage()));
        }
    }

    /** 维修工接单 */
    @PostMapping("/{id}/start")
    public ResponseEntity<?> start(@PathVariable Long id, HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        try {
            repairOrderService.startRepair(id, userId);
            return ResponseEntity.ok(Map.of("message", "接单成功"));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("message", e.getMessage()));
        }
    }

    /** 维修完成 */
    @PostMapping("/{id}/complete")
    public ResponseEntity<?> complete(@PathVariable Long id,
                                      @RequestBody CompleteOrderRequest req,
                                      HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        try {
            repairOrderService.completeRepair(id, req, userId);
            return ResponseEntity.ok(Map.of("message", "维修完成，待验证"));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("message", e.getMessage()));
        }
    }

    /** 验证通过（管理员） */
    @PostMapping("/{id}/verify")
    public ResponseEntity<?> verify(@PathVariable Long id, HttpServletRequest request) {
        String role = (String) request.getAttribute("role");
        if (!"ADMIN".equals(role)) {
            return ResponseEntity.status(403).body(Map.of("message", "只有管理员可以验证"));
        }
        try {
            repairOrderService.verifyPass(id);
            return ResponseEntity.ok(Map.of("message", "验证通过，工单已完成"));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("message", e.getMessage()));
        }
    }

    /** 工单列表（按角色过滤：学生看自己的、维修工看派给自己的、管理员看全部） */
    @GetMapping
    public ResponseEntity<List<RepairOrder>> list(
            @RequestParam(required = false) String status,
            HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        String role = (String) request.getAttribute("role");
        return ResponseEntity.ok(repairOrderService.listOrders(status, userId, role));
    }

    /** 工单详情 */
    @GetMapping("/{id}")
    public ResponseEntity<?> detail(@PathVariable Long id) {
        RepairOrder order = repairOrderService.getOrder(id);
        if (order == null) return ResponseEntity.status(404).body(Map.of("message", "工单不存在"));
        return ResponseEntity.ok(order);
    }
}