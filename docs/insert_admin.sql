USE ai_ops;

-- 先删除可能存在的错误数据
DELETE FROM sys_user WHERE username = 'admin';

-- 插入正确的账号
INSERT INTO sys_user (username, password, real_name, role) 
VALUES ('admin', '$2a$10$mro.AnvwrzsuGi6w87.geeV8vWcgr.DeuKFTcK4CLY1LJX2qhql7C', '超级管理员', 'ADMIN');