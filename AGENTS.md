# JA LiteMOM 协作说明

本文件适用于整个仓库。项目名称为 JA LiteMOM；代码和 Compose 服务继续沿用 `ailitewms`，不要仅为名称统一而修改数据库、存储键或部署项目名。

## 项目入口

- `frontend/src/views/`：Vue 业务页面；`router.ts`：路由权限；`menu.ts`：菜单组织。
- `frontend/src/components/`：共享表格、分页、状态和报表组件。
- `frontend/src/api.ts`、`auth.ts`：请求、登录态和前端权限。
- `backend/app/api.py`：业务 API；`models.py`：模型；`schemas.py`：请求与响应结构。
- `backend/app/permissions.py`、`security.py`：权限定义与接口鉴权。
- `backend/app/main.py`：启动、数据库初始化及现有兼容升级逻辑，修改前检查旧数据影响。
- `backend/app/inspection_*.py`、`bottle_report_word.py`：检验、报告和导出。
- `backend/tests/`、`frontend/tests/`：业务回归与浏览器交互测试。

## 工作方式

1. 先检查 `git status --short`，保留用户已有改动；查清对应页面、API、模型和现有测试。
2. 沿用 Vue Composition API、TypeScript、Element Plus 与 SQLAlchemy 写法，优先复用组件。
3. 用中文解释业务行为、验证结果和限制。代码标识使用现有命名风格。
4. 改动保持范围集中，避免顺便重构大文件、格式化无关代码或重命名公共接口。
5. 新增依赖同步锁文件；前端使用 `npm ci` 还原环境。
6. 完成用户授权的工作后报告结果，不得把未运行的检查说成通过。

## 业务约束

- 抄码核对使用单表。服务端先筛选并对全部结果做异常优先排序，再分页；异常为编号超过 13 位、厂家为空或生产日期为空。
- 查询总数和异常数量覆盖整个筛选结果，不能只统计当前页。表格和汇总使用相同筛选条件。
- 表内编辑和撤销保留接口权限；已检验记录不得撤销，供瓶单位和规格按既有锁定规则处理。
- `coding_customer_id`（抄码客户）与 `source_id`（原供瓶单位／库存归属）不是同一概念。拆单和客户调整不能意外改变原入库、出库及库存归属。
- 日序号、生产年月、抄码日期、检验日期各有语义；抄码业务日期沿用 `Asia/Shanghai` 口径。
- 库存单据生效、作废、撤销和质量变化必须保持库存一致，避免重复扣减或返还。
- 检验单拆分／合并保留历史快照、原序号和追溯关系；重检按原单当前客户分组。
- 报告导出涉及编号、客户模板选择及历史记录。修改时验证业务影响，线上验证优先用只读接口。
- 权限同时在后端校验和前端呈现，隐藏按钮不能代替接口鉴权。

## 常用验证

从根目录运行：

```bash
.venv/bin/python -m pytest backend/tests -q
```

从 `frontend/` 运行：

```bash
npm run build
npm run test:coding-filters
```

浏览器测试通常需要先启动 `npm run dev` 并安装 Chrome，可用 `TEST_BASE_URL`、`CHROME_PATH` 指定本地服务与浏览器。不同测试的数据来源不同，运行前检查脚本。数据库测试只能使用隔离测试库。

按改动选择相关测试，纯文案更改不必重复运行全部业务测试。库存、权限、撤销、拆单和数据库兼容逻辑需要对应回归。

公开仓库不包含业务 Word 模板。完整后端测试中的报告用例需按 `backend/app/templates/README.md` 补齐已授权模板；缺少模板时如实报告，不得自动用生产文件补齐或跳过后宣称全量通过。

## 截图与文档

- README 截图使用虚构数据，保存在 `docs/screenshots/`，保持与实际页面一致。
- `frontend/scripts/readme-screenshots.mjs` 使用本地前端并拦截 API，可用 `npm run docs:screenshots` 重建。
- 用户要求的 `agent.md` 由本文件 `AGENTS.md` 承载，避免两份规则冲突。
- 新增行为同步更新说明，旧版需求文档不应被视为当前实现的唯一来源。

## Git 与发布

- 主分支为 `main`，远程为 `https://github.com/auenger/JA_LiteMOM.git`。
- 不提交 `.env`、密钥、数据库、备份、日志、依赖目录、构建产物、生产截图或业务签名模板。
- 被忽略的私有文件仍可能在本机存在。不要删除，也不要用 `git add -f` 绕过规则。
- 提交前检查暂存区和敏感文件。推送、部署按用户任务授权执行，禁止强制覆盖远程历史。
- 部署参考 `docs/deployment.md`。沿用原 Compose 项目名与数据卷，发布前备份并验证可读性，成功验证后更新当前版本标记。
- 资源有限的服务器使用本地预构建镜像，不得影响同机其他系统。未经明确授权不得删除业务数据或执行 `docker compose down -v`。
