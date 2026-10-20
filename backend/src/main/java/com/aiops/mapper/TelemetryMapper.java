package com.aiops.mapper;

import com.aiops.entity.Telemetry;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface TelemetryMapper extends BaseMapper<Telemetry> {

    /**
     * 真正的批量插入：一条 INSERT 插多条（配合攒批消费，减少 DB 往返次数）
     * 注意：current 是 SQL 保留字，列名必须用反引号包裹
     */
    @Insert("<script>" +
            "INSERT INTO telemetry (device_id, temperature, humidity, `current`, voltage, vibration, ts) VALUES " +
            "<foreach collection='list' item='t' separator=','>" +
            "(#{t.deviceId}, #{t.temperature}, #{t.humidity}, #{t.current}, #{t.voltage}, #{t.vibration}, #{t.ts})" +
            "</foreach>" +
            "</script>")
    int batchInsert(@Param("list") List<Telemetry> list);
}
