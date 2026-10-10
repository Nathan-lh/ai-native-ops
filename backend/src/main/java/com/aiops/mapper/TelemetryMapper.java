package com.aiops.mapper;

import com.aiops.entity.Telemetry;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TelemetryMapper extends BaseMapper<Telemetry> {
}