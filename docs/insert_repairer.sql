USE ai_ops;

DELETE FROM sys_user WHERE username = 'repairer';

INSERT INTO sys_user (username, password, real_name, role) 
VALUES ('repairer', '$2a$10$P6p2nhCyNMufh6mwzAKV6ebZPsGzBzII5nyImQsbIuoyeXJnAFDl6', '维修工张三', 'REPAIRER');