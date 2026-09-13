# 后端项目骨架验证记录

日期：2026-09-12

## 环境

- Python 3.12
- PostgreSQL 16 Alpine
- Redis 7.4 Alpine
- Docker Compose v5.1.0

## 验证结果

1. Python依赖安装成功。
2. `pytest -q`：7 passed；存在1条Starlette依赖内部的弃用警告。
3. Python `compileall`：通过。
4. `docker compose config --quiet`：通过。
5. Alembic离线SQL生成：通过。
6. PostgreSQL真实迁移：`20260912_0001` 执行成功。
7. `alembic check`：`No new upgrade operations detected.`
8. 已创建表：
   - `alembic_version`
   - `authors`
   - `poems`
   - `poem_lines`
   - `tags`
   - `tag_aliases`
   - `poem_tags`
9. Redis健康检查：`PONG`。
10. 真实Redis指纹计数：连续两次计数得到1、2，剩余98。
11. Redis Key有有效TTL，且不包含原始浏览器指纹。
12. `GET /healthz`：`{"status":"ok"}`。
13. `GET /readyz`：数据库与Redis均为 `true`，服务状态为 `ready`。
14. OpenAPI标题：`见景寻诗 API`，版本：`0.1.0`。

## 已处理问题

- Windows缺少IANA时区数据：增加固定版本 `tzdata` 依赖。
- Pydantic Settings默认把逗号分隔列表当JSON解析：改为字符串配置和只读拆分属性。
- PostgreSQL ENUM迁移重复创建：改为迁移显式创建一次，建表阶段只引用已有类型。
- ORM整数类型与迁移BIGINT/SMALLINT不一致：统一模型类型，并通过 `alembic check` 复核。

## 当前边界

当前阶段完成项目基础设施、数据模型、迁移、Redis限流服务与健康检查。图片上传、模型调用、50首唐诗导入和匹配评分接口属于下一阶段。
