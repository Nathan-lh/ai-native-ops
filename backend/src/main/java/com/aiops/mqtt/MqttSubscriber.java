package com.aiops.mqtt;

import com.aiops.config.MqttProperties;
import com.aiops.dto.TelemetryMessage;
import com.aiops.service.TelemetryService;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.eclipse.paho.client.mqttv3.*;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class MqttSubscriber {

    private final MqttProperties mqttProperties;
    private final TelemetryService telemetryService;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private MqttAsyncClient client;

    @PostConstruct
    public void init() {
        try {
            client = new MqttAsyncClient(
                    mqttProperties.getBroker(),
                    mqttProperties.getClientId(),
                    new MemoryPersistence()
            );

            client.setCallback(new MqttCallbackExtended() {
                @Override
                public void connectComplete(boolean reconnect, String serverURI) {
                    log.info("[MQTT] 连接成功，broker: {}", serverURI);
                    try {
                        client.subscribe(mqttProperties.getTopic(), mqttProperties.getQos());
                        log.info("[MQTT] 已订阅主题: {}", mqttProperties.getTopic());
                    } catch (MqttException e) {
                        log.error("[MQTT] 订阅失败", e);
                    }
                }

                @Override
                public void messageArrived(String topic, MqttMessage message) throws Exception {
                    try {
                        String payload = new String(message.getPayload());
                        TelemetryMessage msg = objectMapper.readValue(payload, TelemetryMessage.class);
                        telemetryService.receiveTelemetry(msg); // 丢进队列，不阻塞 MQTT 线程
                    } catch (Exception e) {
                        log.error("[MQTT] 消息解析失败", e);
                    }
                }

                @Override
                public void connectionLost(Throwable cause) {
                    log.warn("[MQTT] 连接断开，尝试重连...", cause);
                }

                @Override
                public void deliveryComplete(IMqttDeliveryToken token) {}
            });

            MqttConnectOptions options = new MqttConnectOptions();
            options.setAutomaticReconnect(true);
            options.setCleanSession(true);
            client.connect(options);

        } catch (MqttException e) {
            log.error("[MQTT] 客户端初始化失败", e);
        }
    }

    @PreDestroy
    public void destroy() {
        try {
            if (client != null && client.isConnected()) {
                client.disconnect();
                client.close();
                log.info("[MQTT] 客户端已关闭");
            }
        } catch (MqttException e) {
            log.error("[MQTT] 关闭失败", e);
        }
    }
}