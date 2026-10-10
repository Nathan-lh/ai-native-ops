USE ai_ops;

-- 添加乐观锁字段，默认值 0
ALTER TABLE repair_order ADD COLUMN version INT NOT NULL DEFAULT 0 COMMENT '乐观锁版本号';

-- 添加乐观锁生效需要的唯一索引优化（可选）
-- （这里不需要，主键就是唯一索引）