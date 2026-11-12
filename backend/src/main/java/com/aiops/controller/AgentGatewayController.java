package com.aiops.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Agent 网关：前端不再直连 Python(8000)，统一走本 Java 网关转发。
 * 好处：
 *   1. 统一 JWT 鉴权（该接口受 Spring Security 保护，前端必须携带登录 Token）
 *   2. 隐藏 Python 服务地址，避免大模型接口暴露公网
 *   3. 可在网关层做限流、审计
 */
@Slf4j
@RestController
@RequestMapping("/api/agent")
public class AgentGatewayController {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${agent.base-url:http://localhost:8000}")
    private String agentBaseUrl;

    // SSE 是长连接，每个连接占用一个线程，需独立于业务线程池
    private final ExecutorService executor = Executors.newCachedThreadPool();

    @PostMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter chatStream(@RequestBody Map<String, String> body) {
        SseEmitter emitter = new SseEmitter(0L);

        executor.submit(() -> {
            try {
                String payload = objectMapper.writeValueAsString(body);

                HttpClient client = HttpClient.newBuilder()
                        // uvicorn 只支持 HTTP/1.1，Java 默认的 HTTP/2(h2c) 升级会被其拒绝返回 422
                        .version(HttpClient.Version.HTTP_1_1)
                        .connectTimeout(Duration.ofSeconds(5))
                        .build();
                HttpRequest pyReq = HttpRequest.newBuilder()
                        .uri(URI.create(agentBaseUrl + "/api/chat/stream"))
                        .header("Content-Type", "application/json")
                        .timeout(Duration.ofMinutes(5))
                        .POST(HttpRequest.BodyPublishers.ofString(payload, StandardCharsets.UTF_8))
                        .build();

                HttpResponse<InputStream> resp = client.send(
                        pyReq, HttpResponse.BodyHandlers.ofInputStream());

                // 逐行解析 Python 的 SSE 输出（event:/data: 空行分隔）并透传给前端
                BufferedReader reader = new BufferedReader(
                        new InputStreamReader(resp.body(), StandardCharsets.UTF_8));
                String line;
                String eventName = "message";
                StringBuilder data = new StringBuilder();
                while ((line = reader.readLine()) != null) {
                    if (line.startsWith("event:")) {
                        eventName = line.substring(6).trim();
                    } else if (line.startsWith("data:")) {
                        String d = line.substring(5).trim();
                        if (data.length() > 0) {
                            data.append("\n");
                        }
                        data.append(d);
                    } else if (line.isEmpty() && data.length() > 0) {
                        emitter.send(SseEmitter.event().name(eventName).data(data.toString()));
                        data.setLength(0);
                        eventName = "message";
                    }
                }
                // 处理末尾没有空行分隔的最后一个事件
                if (data.length() > 0) {
                    emitter.send(SseEmitter.event().name(eventName).data(data.toString()));
                }
                emitter.complete();
            } catch (Exception e) {
                log.error("[Agent网关] SSE 代理异常", e);
                emitter.completeWithError(e);
            }
        });

        return emitter;
    }

    @PreDestroy
    public void destroy() {
        executor.shutdown();
    }
}
