UPDATE sys_user SET id=1 WHERE username='admin';
UPDATE sys_user SET id=2 WHERE username='repairer';
UPDATE sys_user SET id=3 WHERE username='student';

UPDATE repair_order SET reporter_id=1 WHERE reporter_id=4;
UPDATE repair_order SET reviewer_id=1 WHERE reviewer_id=4;
UPDATE repair_order SET repairer_id=2 WHERE repairer_id=5;
UPDATE repair_order SET reporter_id=3 WHERE reporter_id=6;
UPDATE repair_order SET reviewer_id=3 WHERE reviewer_id=6;
UPDATE repair_order SET repairer_id=3 WHERE repairer_id=6;

UPDATE knowledge_candidate SET reviewer_id=1 WHERE reviewer_id=4;

SELECT id, username, real_name, role FROM sys_user ORDER BY id;