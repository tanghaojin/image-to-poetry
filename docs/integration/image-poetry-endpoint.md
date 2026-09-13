# 图片理解与诗词匹配统一接口

日期：2026-09-13

## 请求

`POST /api/v1/poetry/match`

- Content-Type：`multipart/form-data`
- 表单字段：`image`
- 支持格式：JPG、PNG、WebP
- 最大原始文件：10 MB
- 必需请求头：`X-Device-Fingerprint`
- 可选请求头：`X-Request-ID`

## 服务端处理顺序

1. 校验文件大小、声明类型与真实图片内容。
2. 修正 EXIF 方向，最长边压缩到 1600 像素，透明区域铺浅色背景，转换为质量 85 的 JPEG 内存副本。
3. Redis 使用浏览器指纹的 HMAC-SHA256 摘要按香港自然日原子计数；默认每天 100 次。
4. 按配置顺序调用图片模型：`gemini-3.7-flash`、`gemini-3.6-flash`、`glm-4.6v-flash`、`glm-4.1v-thinking-flash`。
5. 将模型结果归一化为单一意境和结构化画面信息。
6. 只在已启用且已人工复核的标签中匹配真实古诗，返回唯一结果。

模型密钥、Base64 图片内容和原始浏览器指纹均不写入日志或数据库。

## 成功响应

响应包含：

- `requestId`
- `understanding`：主体、季节、时段、天气、最高可信意境、画面总结、可信度
- `poem`：诗词标识、标题、作者、朝代、体裁、全诗分句、精选句索引
- `match`：分数、命中标签、理由、算法版本
- `meta.processingMs`：服务端处理耗时

## 失败响应

- 图片缺失或内容异常：400 / 413 / 415 / 422
- 指纹缺失：400
- 当日配额超过 100 次：429，前端显示“服务器繁忙，请稍后再试”
- PostgreSQL 或 Redis 不可用：503
- 所有图片模型均失败：502
- 图片理解与匹配总时间超过 45 秒：504

## 验证记录

- 后端自动化测试：21 项通过，包含统一 multipart 接口契约测试。
- 真实图片服务端调用：首选 Gemini 模型繁忙时，成功回退到下一候选模型并返回结构化理解结果。
- 依赖不可用检查：真实 HTTP 接口返回 503 和 `DEPENDENCY_UNAVAILABLE`，未绕过 Redis 配额保护。
- 真实 PostgreSQL/Redis 参与的统一接口和浏览器页面闭环，待本地主机 Docker Desktop 恢复后补充验证。
