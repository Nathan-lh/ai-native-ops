package com.aiops.controller;

import com.aiops.dto.LoginRequest;
import com.aiops.dto.RegisterRequest;
import com.aiops.entity.SysUser;
import com.aiops.mapper.SysUserMapper;
import com.aiops.utils.JwtUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final SysUserMapper sysUserMapper;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;
    private final StringRedisTemplate redis;

    // 演示用邀请码（生产环境应存数据库或配置中心）
    private static final String ADMIN_INVITE_CODE = "ADMIN2026";
    private static final String REPAIRER_INVITE_CODE = "REPAIR2026";

    // ==================== 登录 ====================
    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody LoginRequest req) {
        SysUser user = sysUserMapper.selectOne(
                new LambdaQueryWrapper<SysUser>().eq(SysUser::getUsername, req.getUsername()));

        // 分开提示：账号不存在 vs 密码错误
        if (user == null) {
            return ResponseEntity.status(401).body(Map.of("message", "账号不存在"));
        }
        if (!passwordEncoder.matches(req.getPassword(), user.getPassword())) {
            return ResponseEntity.status(401).body(Map.of("message", "密码错误"));
        }

        String token = jwtUtil.generateToken(user.getId(), user.getUsername(), user.getRole());

        // 单点登录：最新 token 覆盖旧的，旧 token 立即失效（7 天有效）
        redis.opsForValue().set(
                "login:token:" + user.getId(),
                token,
                7, TimeUnit.DAYS
        );

        Map<String, Object> result = new HashMap<>();
        result.put("token", token);
        result.put("username", user.getUsername());
        result.put("realName", user.getRealName());
        result.put("role", user.getRole());
        return ResponseEntity.ok(result);
    }

    // ==================== 注册 ====================
    @PostMapping("/register")
    public ResponseEntity<?> register(@RequestBody RegisterRequest req) {
        // 1. 基础字段校验
        if (req.getUsername() == null || req.getUsername().length() < 3) {
            return ResponseEntity.badRequest().body(Map.of("message", "用户名至少 3 位"));
        }
        if (req.getPassword() == null || req.getPassword().length() < 6) {
            return ResponseEntity.badRequest().body(Map.of("message", "密码至少 6 位"));
        }
        if (req.getRealName() == null || req.getRealName().isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("message", "请填写真实姓名"));
        }

        // 2. 用户名唯一性
        Long exist = sysUserMapper.selectCount(
                new LambdaQueryWrapper<SysUser>().eq(SysUser::getUsername, req.getUsername()));
        if (exist != null && exist > 0) {
            return ResponseEntity.badRequest().body(Map.of("message", "用户名已存在"));
        }

        // 3. 角色合法性
        String role = req.getRole();
        if (!List.of("STUDENT", "TEACHER", "REPAIRER", "ADMIN").contains(role)) {
            return ResponseEntity.badRequest().body(Map.of("message", "无效的角色"));
        }

        // 4. 邀请码校验
        if ("ADMIN".equals(role)) {
            if (!ADMIN_INVITE_CODE.equals(req.getInviteCode())) {
                return ResponseEntity.badRequest().body(Map.of("message", "管理员邀请码错误"));
            }
        } else if ("REPAIRER".equals(role)) {
            if (!REPAIRER_INVITE_CODE.equals(req.getInviteCode())) {
                return ResponseEntity.badRequest().body(Map.of("message", "维修工邀请码错误"));
            }
        }
        // STUDENT / TEACHER 不需要邀请码

        // 5. 创建用户
        SysUser user = new SysUser();
        user.setUsername(req.getUsername());
        user.setPassword(passwordEncoder.encode(req.getPassword()));
        user.setRealName(req.getRealName());
        user.setPhone(req.getPhone());
        user.setRole(role);
        user.setCreateTime(LocalDateTime.now());
        user.setUpdateTime(LocalDateTime.now());
        sysUserMapper.insert(user);

        return ResponseEntity.ok(Map.of("message", "注册成功", "userId", user.getId()));
    }

    // ==================== 当前用户信息 ====================
    @GetMapping("/me")
    public Map<String, Object> me(HttpServletRequest request) {
        Map<String, Object> result = new HashMap<>();
        result.put("userId", request.getAttribute("userId"));
        result.put("username", request.getAttribute("username"));
        result.put("role", request.getAttribute("role"));
        return result;
    }

    @GetMapping("/debug/hash")
    public String debugHash(@RequestParam String raw) {
        return passwordEncoder.encode(raw);
    }
}