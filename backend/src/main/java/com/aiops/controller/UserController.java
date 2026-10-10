package com.aiops.controller;

import com.aiops.entity.SysUser;
import com.aiops.mapper.SysUserMapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 用户相关接口（管理员用来查维修工列表等）
 */
@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

    private final SysUserMapper sysUserMapper;

    /**
     * 查询所有维修工（仅管理员可见）
     * 返回：id、username、realName、phone
     */
    @GetMapping("/repairers")
    public ResponseEntity<?> listRepairers(HttpServletRequest request) {
        String role = (String) request.getAttribute("role");
        if (!"ADMIN".equals(role)) {
            return ResponseEntity.status(403).body(Map.of("message", "只有管理员可以查看维修工列表"));
        }

        List<SysUser> users = sysUserMapper.selectList(
                new LambdaQueryWrapper<SysUser>()
                        .eq(SysUser::getRole, "REPAIRER")
                        .orderByAsc(SysUser::getId));

        // 只返回必要字段，不暴露密码
        List<Map<String, Object>> result = users.stream().map(u -> {
            Map<String, Object> m = new HashMap<>();
            m.put("id", u.getId());
            m.put("username", u.getUsername());
            m.put("realName", u.getRealName());
            m.put("phone", u.getPhone());
            return m;
        }).collect(Collectors.toList());

        return ResponseEntity.ok(result);
    }
}