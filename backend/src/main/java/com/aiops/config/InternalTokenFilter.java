package com.aiops.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * 服务间鉴权过滤器：保护 /api/agent/tools/** 这类只给 Python Agent 内网调用的接口。
 * 校验请求头 X-Internal-Token 是否与后端配置一致，防止接口被公网裸调。
 */
@Slf4j
@Component
public class InternalTokenFilter extends OncePerRequestFilter {

    private static final String TOOL_PATH_PREFIX = "/api/agent/tools/";
    private static final String HEADER_NAME = "X-Internal-Token";

    @Value("${agent.internal-token:}")
    private String internalToken;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {

        if (request.getRequestURI().startsWith(TOOL_PATH_PREFIX)) {
            String token = request.getHeader(HEADER_NAME);
            if (internalToken == null || internalToken.isEmpty() || !internalToken.equals(token)) {
                log.warn("[内部鉴权] /api/agent/tools 请求 token 校验失败, uri={}", request.getRequestURI());
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                response.setContentType("application/json;charset=UTF-8");
                response.getWriter().write("{\"code\":401,\"message\":\"内部接口鉴权失败\"}");
                return;
            }
        }
        chain.doFilter(request, response);
    }
}
