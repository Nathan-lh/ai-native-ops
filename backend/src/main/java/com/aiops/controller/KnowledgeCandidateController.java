package com.aiops.controller;

import com.aiops.entity.KnowledgeCandidate;
import com.aiops.service.KnowledgeCandidateService;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 知识候选 Controller
 * 接口列表：
 *   GET  /api/knowledge/candidates              分页查询候选
 *   POST /api/knowledge/candidates/{id}/approve 审核通过
 *   POST /api/knowledge/candidates/{id}/reject  审核驳回
 *   GET  /api/knowledge/candidates/approved     查询已通过（供 Python 回流用）
 */
@RestController
@RequestMapping("/api/knowledge/candidates")
@RequiredArgsConstructor
public class KnowledgeCandidateController {

    private final KnowledgeCandidateService candidateService;

    /** 分页查询候选列表 */
    @GetMapping
    public ResponseEntity<?> list(
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size) {
        Page<KnowledgeCandidate> p = candidateService.listPage(status, page, size);
        return ResponseEntity.ok(Map.of(
                "total", p.getTotal(),
                "page", page,
                "size", size,
                "list", p.getRecords()
        ));
    }

    /** 审核通过（管理员） */
    @PostMapping("/{id}/approve")
    public ResponseEntity<?> approve(@PathVariable Long id,
                                     @RequestBody(required = false) Map<String, String> body,
                                     HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        String role = (String) request.getAttribute("role");
        if (!"ADMIN".equals(role)) {
            return ResponseEntity.status(403).body(Map.of("message", "只有管理员可以审核"));
        }
        String comment = body != null ? body.get("comment") : null;
        try {
            candidateService.approve(id, userId, comment);
            return ResponseEntity.ok(Map.of("message", "审核通过"));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("message", e.getMessage()));
        }
    }

    /** 审核驳回（管理员） */
    @PostMapping("/{id}/reject")
    public ResponseEntity<?> reject(@PathVariable Long id,
                                    @RequestBody(required = false) Map<String, String> body,
                                    HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        String role = (String) request.getAttribute("role");
        if (!"ADMIN".equals(role)) {
            return ResponseEntity.status(403).body(Map.of("message", "只有管理员可以审核"));
        }
        String comment = body != null ? body.get("comment") : null;
        try {
            candidateService.reject(id, userId, comment);
            return ResponseEntity.ok(Map.of("message", "已驳回"));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("message", e.getMessage()));
        }
    }

    /** 查询所有已通过审核的候选（供 Python 端回流知识库用，无需登录） */
    @GetMapping("/approved")
    public ResponseEntity<List<KnowledgeCandidate>> approved() {
        return ResponseEntity.ok(candidateService.listApproved());
    }
}