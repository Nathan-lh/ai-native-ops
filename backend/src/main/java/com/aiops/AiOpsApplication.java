package com.aiops;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 应用启动类 —— 整个后端的入口
 *
 * @SpringBootApplication 是组合注解，等于：
 *   @SpringBootConfiguration + @EnableAutoConfiguration + @ComponentScan
 * 作用：自动配置 + 扫描当前包及子包下的所有组件（Controller/Service/Mapper 等）
 */
@SpringBootApplication
@MapperScan("com.aiops.mapper")
public class AiOpsApplication {

    public static void main(String[] args) {
        // 启动 Spring Boot 应用（内嵌 Tomcat，默认监听 8080 端口）
        SpringApplication.run(AiOpsApplication.class, args);
    }
}