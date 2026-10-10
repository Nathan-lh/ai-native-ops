package com.aiops.dto;

import lombok.Data;

@Data
public class RegisterRequest {
    private String username;
    private String password;
    private String realName;
    private String phone;
    private String role;
    /** 管理员/维修工注册时需要 */
    private String inviteCode;
}