# 诗词匹配接口验证

## 实现范围

- 接口：`POST /api/v1/poems/match`
- 详情：`GET /api/v1/poems/{poem_slug}`
- 算法：`tag-score-v1`
- 候选门禁：只读取 `verification_status = verified` 且 `reviewed = true` 的启用标签
- 排序：匹配分降序、名篇优先级降序、数据库 ID 升序，保证结果稳定

## 评分规则

- 主体 0.35、季节 0.12、时段 0.08、天气 0.15、情绪 0.22
- 多主体按最高匹配与主体覆盖率组合计分，避免标签数量较多的诗天然占优
- 同义表达先归一化，例如“孤舟/小舟/扁舟”统一到舟船，“秋天/秋季”统一到秋
- 语义分与名篇优先级组合，并使用图片理解置信度做小幅校准
- 匹配理由使用确定性模板生成；诗句始终来自本地标准正文

## 验证结果

- 自动化测试：11 项通过
- 雪景、孤舟、江河、冬、孤寂：返回柳宗元《江雪》
- 秋夜、明月、思乡：返回李白《关山月》
- 反转候选列表后返回结果不变
- 真实 FastAPI → PostgreSQL 调用成功
- 超过 5 个主体返回 HTTP 422；不存在的诗词返回 HTTP 404 / `POEM_NOT_FOUND`
- OpenAPI 已包含 `/api/v1/poems/match`
- `/healthz` 为 `ok`，`/readyz` 的 PostgreSQL 和 Redis 均为 `true`
