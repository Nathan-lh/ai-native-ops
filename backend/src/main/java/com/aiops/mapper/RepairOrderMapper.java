package com.aiops.mapper;

import com.aiops.entity.RepairOrder;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Update;

import java.time.LocalDateTime;

@Mapper
public interface RepairOrderMapper extends BaseMapper<RepairOrder> {

    /**
     * CAS 状态流转：把「状态前置校验」从 Java 内存判断下沉到 SQL 的 WHERE 条件，
     * 配合 version 乐观锁，保证并发下只有一个请求能成功流转状态。
     * 返回影响行数：0 表示状态已被他人变更或 version 已过期。
     */

    /** 驳回：PENDING_REVIEW -> REJECTED */
    @Update("UPDATE repair_order SET status = 'REJECTED', reviewer_id = #{reviewerId}, " +
            "review_comment = #{reviewComment}, review_time = #{reviewTime}, version = version + 1 " +
            "WHERE id = #{id} AND status = 'PENDING_REVIEW' AND version = #{version}")
    int casReject(@Param("id") Long id,
                  @Param("reviewerId") Long reviewerId,
                  @Param("reviewComment") String reviewComment,
                  @Param("reviewTime") LocalDateTime reviewTime,
                  @Param("version") Integer version);

    /** 接单：ASSIGNED -> REPAIRING */
    @Update("UPDATE repair_order SET status = 'REPAIRING', version = version + 1 " +
            "WHERE id = #{id} AND status = 'ASSIGNED' AND version = #{version}")
    int casStartRepair(@Param("id") Long id, @Param("version") Integer version);

    /** 维修完成：REPAIRING -> VERIFYING */
    @Update("UPDATE repair_order SET status = 'VERIFYING', repair_comment = #{repairComment}, " +
            "repair_reason = #{repairReason}, complete_time = #{completeTime}, version = version + 1 " +
            "WHERE id = #{id} AND status = 'REPAIRING' AND version = #{version}")
    int casCompleteRepair(@Param("id") Long id,
                          @Param("repairComment") String repairComment,
                          @Param("repairReason") String repairReason,
                          @Param("completeTime") LocalDateTime completeTime,
                          @Param("version") Integer version);

    /** 验证通过：VERIFYING -> COMPLETED */
    @Update("UPDATE repair_order SET status = 'COMPLETED', version = version + 1 " +
            "WHERE id = #{id} AND status = 'VERIFYING' AND version = #{version}")
    int casVerifyPass(@Param("id") Long id, @Param("version") Integer version);
}
