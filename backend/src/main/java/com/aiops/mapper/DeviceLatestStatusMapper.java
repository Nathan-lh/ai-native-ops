package com.aiops.mapper;

import com.aiops.entity.DeviceLatestStatus;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface DeviceLatestStatusMapper extends BaseMapper<DeviceLatestStatus> {

    /**
     * 插入或更新设备状态快照（一条 SQL 完成，省去原来"先 SELECT 再 INSERT/UPDATE"的一次往返）
     */
    @Insert("INSERT INTO device_latest_status (device_id, status, last_seen, last_metric_json, updated_at) " +
            "VALUES (#{deviceId}, #{status}, #{lastSeen}, #{lastMetricJson}, #{updatedAt}) " +
            "ON DUPLICATE KEY UPDATE " +
            "status = VALUES(status), last_seen = VALUES(last_seen), " +
            "last_metric_json = VALUES(last_metric_json), updated_at = VALUES(updated_at)")
    int upsert(DeviceLatestStatus snapshot);
}
