package com.aiops.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("lab_room")
public class LabRoom {

    @TableId(type = IdType.AUTO)
    private Long id;

    private String roomName;

    private String location;

    private Integer capacity;

    private String status;

    private String description;

    private LocalDateTime createTime;

    private LocalDateTime updateTime;
}