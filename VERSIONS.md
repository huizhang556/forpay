# ForPay 版本功能记录

本文件记录每个版本实际完成的功能、修复和验证结果。每个 `vX.Y.Z` 章节必须与同名 Git tag 对应：版本号一致，tag 中列出的每项主要更新都必须在章节中出现，章节不得混入其他版本内容。发布前必须逐项核对 `git show vX.Y.Z` 与本文件；Git tag 由项目维护者手动创建。

## v0.1.3

### 部署脚本网络预检与故障提示（追加）

- 一键安装脚本在拉取镜像前校验 Compose 配置，尽早发现必填变量或 YAML 配置错误。
- 增加 Docker Hub 连通性预检，明确区分镜像仓库网络故障与 ForPay 应用故障；Docker Hub 返回 `401` 视为网络可达。
- README 补充首次拉取耗时、TLS 超时和重试期间的操作说明。

### 海外与中国大陆镜像源部署说明（追加）

- 安装脚本识别 Docker Engine 已配置的 registry mirror，配置加速源时跳过 Docker Hub 直连预检。
- README 区分海外直连与中国大陆镜像加速部署路径，补充 `daemon.json` 配置、重启和验证命令。
- 增加可信私有镜像仓库替代方案，避免使用来源不明的公共代理。

### 一键备份迁移脚本（追加）

- 新增 `scripts/backup-migrate.sh`，支持交互式本机备份和异地迁移两种模式。
- 本机模式导出 PostgreSQL、二维码文件和 `.env`，按时间戳生成压缩备份包。
- 异地模式通过 SSH 创建目标目录并使用 `scp` 复制备份包，支持自定义目标 IP、端口和路径。
- 更新脚本同步增加 Docker registry mirror 识别和 Docker Hub 连通性提示。

本版本汇总 0.1.2 之后完成的支付一致性、回调可靠性、部署安全、运维脚本和文档更新。

### 支付通知与回调一致性加固（追加）

- 支付通知写入改用数据库唯一约束处理并发重复通知，避免相同 `external_id` 导致 500。
- 支付匹配、支付事件和回调任务入队合并到同一事务，降低状态不一致风险。
- 增加订单级回调任务去重，避免重复创建有效回调任务。
- 验证：Ruff 检查通过，Pytest 15 项通过。

### 回调 Worker 多实例领取与故障恢复

- 回调任务增加 `processing_at`，Worker 领取后先提交处理中状态再执行网络请求，减少多实例重复投递。
- 处理超过 10 分钟的任务可自动重新领取，降低进程崩溃导致任务永久卡死的风险。
- Worker 周期异常改为记录结构化异常日志；回调失败会释放处理中状态并按原有退避策略重试。
- 增加 Alembic 迁移 `a1b2c3d4e5f6_callback_processing_lease`。
- 验证：Ruff 检查通过，Pytest 15 项通过。

### Compose 生产配置安全修正

- 移除 Compose 中写死的 PostgreSQL 默认密码，新增必选 `POSTGRES_PASSWORD` 配置。
- API、worker 与 PostgreSQL 容器统一使用 `POSTGRES_PASSWORD` 生成连接配置，避免 `.env` 密码被覆盖。
- 修正文档中的 API 默认端口说明为 7500，并补充密码 URL 编码提示。
- 验证：Ruff 检查通过，Pytest 15 项通过，`docker compose config` 通过。

### 容器供应链与运行权限加固

- 前端镜像依赖安装改用 `npm ci`，提高构建可复现性。
- 生产 Python 镜像仅安装运行时依赖，不再安装 dev 依赖。
- API 和 worker 容器改用非 root 的 `forpay` 用户运行，并限制应用目录权限。
- 验证：Ruff 检查通过，Docker 镜像构建成功。

### Linux 一键运维脚本

- 新增 `scripts/install.sh`：生成缺失密钥、校验 Compose 配置、拉取镜像并启动服务。
- 新增 `scripts/update.sh`：更新前自动备份 PostgreSQL 和二维码文件，再拉取远程最新镜像。
- 新增 `scripts/uninstall.sh`：默认保留数据卷，只有输入 `DELETE-FORPAY` 并使用 `--purge-data` 才删除数据。
- 安装脚本重复执行时保留已有数据库密码和密钥，避免破坏现有数据卷。

### 卸载数据保留确认

- 卸载脚本现在会交互询问是否保留 PostgreSQL、Redis 和二维码数据。
- 选择删除数据时仍需输入 `DELETE-FORPAY` 二次确认；默认回车保留数据。

### 镜像拉取失败重试与排查说明

- 安装和更新脚本对 Docker 镜像拉取增加 3 次递增等待重试。
- 拉取持续失败时明确提示检查 DNS、出口防火墙、代理和 Docker 镜像加速，不会误判为应用故障。
- README 增加 `registry-1.docker.io` TLS 超时排查步骤。

### README 三种部署方式梳理

- 将部署入口统一整理为“一键脚本安装（小白推荐）”“Docker Compose 部署（生产推荐）”和“Linux 本地源码部署”三种方式。
- 增加三种方式的适用对象、特点、前置条件和命令入口说明。
- 区分脚本自动安装流程与手动 Compose 流程，补充卸载数据保留提示。

### 镜像与端口部署修正

- 修正远程镜像部署流程，使用 `docker compose pull` 后再启动，源码构建单独使用 `FORPAY_IMAGE=forpay:local`。
- 增加 `docker compose config --images` 镜像来源核对，远程部署默认使用 `litehub/forpay:latest`。
- 增加可配置的 `FORPAY_API_PORT`，并将 API 宿主机默认端口统一调整为 7500，同步前端代理、健康检查和 Nginx 示例。

### 面向用户移除本地开发入口

- 删除 README 中“一键本地开发”章节及 Windows/Linux 开发启动命令。
- 保留面向用户的三种 Linux 部署方式；开发脚本仅作为项目维护者内部工具，不纳入用户部署流程。

### 部署文档与更新流程重组

- 补齐 Docker Compose 和 Linux 源码部署示例中的 `FORPAY_API_PORT` 等当前配置。
- 删除 README 独立的“测试和质量检查”和“在线更新”章节，避免把维护者检查项混入用户部署说明。
- 将一键脚本、Compose 拉取镜像、源码 `git pull` 三种在线更新流程分别放入对应部署方式。

### 部署变更影响复核

- 修正 `docs/DEPLOYMENT.md` 中遗留的 8000 端口排查命令，统一为默认 7500。
- 补充 Compose 部署必须设置 `POSTGRES_PASSWORD` 的说明。
- 从用户配置模板移除已不再作为部署功能的签名更新清单参数，避免产生无效配置。
- 验证：Pytest 15 项通过，Ruff、三个 Shell 脚本语法和 Compose 配置均通过。

### 补充一键脚本获取位置

- README 明确说明安装、更新、卸载脚本位于仓库根目录 `scripts/` 文件夹。
- 增加 GitHub 克隆、进入项目目录和脚本直接链接，用户无需猜测脚本位置。

### 新增本地开发指南

- 新增一级目录文件 `LOCAL_DEVELOP_GUID.md`，仅供开发者本地记录开发细节和提交问题。
- 该文件已加入 `.gitignore`，不上传 GitHub/Docker Hub，也不出现在用户部署文档中。

### 清理重复开发文档

- 删除早期创建的 `docs/DEVELOPMENT.md`，避免与本地开发记录文件重复。

## v0.1.2

### 本次发布：部署、会话与更新安全完善

- Compose 应用和 worker 镜像统一使用 `forpay`，并修复旧容器切换及 worker 健康检查问题。
- 管理接口增加统一鉴权，管理员会话支持签名、随机数、有效期、状态探测和登出。
- 在线更新清单增加 HTTPS、DNS 解析和非公网地址 SSRF 防护。
- README 补充统一部署流程、配置分级和生产上线检查清单。
- 增加登录、登出和敏感接口鉴权测试，完成后端、前端和 Compose 构建验证。

## v0.1.1

### 本次修复：镜像命名、管理会话与在线更新安全

- Compose 构建的 app 与 worker 镜像统一命名为 `forpay`。
- 仪表盘、订单列表和订单详情增加管理员鉴权，未登录请求统一返回 401。
- 管理员会话改为带随机数、HMAC 签名和 1 小时有效期的 Cookie，新增会话探测与登出接口。
- 前端启动时校验服务端登录状态，支持服务端登出后自动回到登录页。
- 在线更新清单增加 HTTPS 凭据、自定义端口限制及 DNS 解析后的私网、回环、链路本地和保留地址拦截。
- 增加登录、登出和敏感接口鉴权测试。

### 本次文档优化：部署流程梳理

- README 新增统一部署总流程和上线前检查清单。
- 明确必选、建议和可选配置的优先级，补充健康检查、备份、升级和回滚前置要求。

### 本次修复：Compose 镜像切换与 worker 健康检查

- 修复旧容器仍引用 `forpay-app`、`forpay-worker` 的问题，重新创建后统一使用 `forpay:latest`。
- 禁用 worker 继承的 API 健康检查，避免 worker 因不监听 8000 端口被错误标记为 unhealthy。

### 本次修复：旧版数据库启动迁移兼容

- 修复旧部署使用 `create_all` 创建表但缺少 `alembic_version` 时，启动重复建表导致 `DuplicateTable` 和 app unhealthy 的问题。
- 增加 `scripts/migrate.py`：仅当检测到完整旧版 ForPay 表且没有迁移版本记录时执行 `stamp head`，新数据库仍执行正常 Alembic migration。
- Docker 启动脚本改为固定调用兼容迁移入口，并在迁移失败时输出明确错误。

### 本次修复：Docker 首次启动迁移

- 修复 Docker 镜像遗漏 `alembic.ini` 导致 `No 'script_location' key found in configuration`、app 无法启动的问题。
- Docker 启动命令显式使用 `/app/alembic.ini`，不再依赖当前工作目录查找 Alembic 配置。
- README 增加首次启动迁移失败的排查提示。

### 本次补充：启动脚本和生产配置修复

- 增加独立 `scripts/start-api.sh`，固定在 `/app` 工作目录读取 `/app/alembic.ini`。
- 启动前检查 Alembic 配置和 `script_location`，通过 `python -m alembic -c /app/alembic.ini upgrade head` 执行迁移。
- 进一步避免因工作目录或默认配置错误导致的 Alembic 启动失败。
- 移除 Compose 对 `FORPAY_CORS_ORIGINS` 的强制覆盖，生产环境可正确使用 `.env` 中的域名配置。
- 增加 API 健康检查 `start_period`，避免数据库迁移期间被过早判定为 unhealthy。

### 本次补充：项目结构文档

- 新增 `docs/API.md`，整理管理端、商户下单、支付页、二维码、到账通知、回调、指标和更新接口。
- 新增 `docs/ARCHITECTURE.md`，说明 API、Redis、PostgreSQL、worker 的组件关系和订单数据流。
- 新增 `docs/DEPLOYMENT.md`，说明 Docker Compose、Linux 源码部署、systemd、Nginx、备份和升级。
- 新增 `docs/SECURITY.md`，集中说明密钥、订单、二维码、SSRF、WAF、CORS 和部署安全。
- 新增 `docs/TROUBLESHOOTING.md`，整理 API、worker、Cookie、二维码、到账通知、回调和镜像故障排查。
- 新增 `docs/DEVELOPMENT.md`，说明开发初始化、测试命令、修改规范和版本提交流程。
- README 增加结构文档索引，方便用户按场景查阅。

### 本次补充：部署配置文档

- README 增加 Docker Compose 独立配置示例，明确 `postgres` 和 `redis` 容器服务名不能改为 `localhost`。
- README 增加 Linux 源码部署独立配置示例，明确本机 PostgreSQL 和 Redis 使用 `127.0.0.1`。
- 两套示例均列出生产必填密钥、数据库、Redis、CORS、订单有效期、连接池、限流、WAF、指标和在线更新配置。
- 补充四个核心密钥必须互不相同、`.env` 必须使用 `600` 权限、API 和 worker 必须共用同一配置的说明。

### 主要更新

- 完善回调地址 SSRF 防护：校验协议、用户信息、DNS 解析结果，并拒绝私有、回环、保留和未指定地址。
- 回调请求关闭自动重定向，发送前再次验证回调地址，降低 DNS 解析和跳转造成的内网访问风险。
- 增加独立 `FORPAY_ENCRYPTION_KEY`，生产环境拒绝默认密钥、短密钥和缺失密钥。
- Fernet 敏感数据加密支持独立密钥管理。
- 增加统一参数校验、HTTP 异常和未处理异常响应，避免暴露内部堆栈。
- 增加回调失败、WAF 拦截和未处理异常日志，禁止日志记录密钥和完整通知原文。
- 增加 PostgreSQL 连接池大小、溢出连接数和超时配置。
- 增加 SQLAlchemy 异步引擎，并在应用退出时释放连接池。
- 增加 Prometheus 请求计数和延迟指标，`/metrics` 仅允许管理员令牌访问。
- 严格限制 CORS 请求方法和请求头，禁止通配来源。
- 前端页面改为 React lazy 动态加载，拆分 Dashboard、订单、通道和支付页面资源。
- 增加基础 WAF，拦截常见 SQL 注入、脚本注入、路径穿越和编码探测载荷。
- 增加静态资源长期缓存，支付 API、订单、二维码、管理端和指标接口禁止缓存。
- 将健康检查路由拆分到独立 API 模块。
- 增加 SSRF、更新签名、指标鉴权、WAF、checkout token 和性能基线测试。
- 单元测试覆盖率达到 66%。
- 补充 Linux Docker Compose、源码部署、Nginx、安全和运维说明。

### 验证结果

- Ruff 检查通过。
- Pytest 13 项通过。
- 覆盖率 66%。
- 前端生产构建通过。
- Docker Compose 配置校验通过。
- 已通过真实 HTTP 请求验证健康检查、管理员登录、通道创建、订单创建、checkout 会话保护、指标鉴权和到账通知匹配。

### 已知限制

- Docker 构建测试曾受 Docker Hub 网络授权失败影响，本地 API、PostgreSQL 和 Redis 功能已完成验证。
- 当前业务路由仍以同步 SQLAlchemy 为主，异步引擎已准备但尚未完成全部业务接口迁移。
- 内置 WAF 是基础过滤器，生产环境仍应在 Nginx 或云 WAF 层增加规则。
- 正式承载资金前仍需完成 DNS 级 SSRF 出口策略、管理员 RBAC、Android 设备凭据、数据库恢复演练和并发压测。



## v0.1.0

### 主要更新

- 建立 FastAPI、React、PostgreSQL、Redis 和 Docker Compose 基础工程。
- 实现微信、支付宝静态二维码通道、二维码上传校验和私有文件读取。
- 实现订单创建、产品结算、公开支付页、订单有效期和并发金额尾数分配。
- 实现到账通知幂等、自动匹配、人工补单、支付事件记录和回调重试队列。
- 实现商户 API Key、HMAC 签名、时间戳防重放、幂等键和 Redis 分布式限流。
- 实现管理员会话、监控端令牌、请求体限制、安全响应头和基础 SSRF 防护。
- 实现订单 token 绑定的 checkout Cookie，保护二维码接口免受直接 URL 抓取。
- 实现过期订单 worker，避免已过期金额尾数长期占用。
- 实现 Ed25519 签名更新清单检查，但禁止在线自动执行远程代码。
- 补充 Linux Docker Compose、源码部署、Nginx、API、安全和运维说明。

### 已知限制

二维码仍然是人工上传的静态收款码。没有微信或支付宝官方 API 时，系统无法生成官方指定金额收款码；只能通过短有效期、唯一金额、到账匹配、通知去重和人工复核降低风险。
