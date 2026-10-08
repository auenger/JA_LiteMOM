# README 截图

图片来自实际 Vue 页面，业务内容由 `frontend/scripts/readme-screenshots.mjs` 的虚构数据提供，不连接生产后端。

| 图片 | 内容 |
| --- | --- |
| `dashboard.png` | 库存、日月年汇总、低库存预警 |
| `coding.png` | 单表抄码核对、异常标黄、查询与分页 |
| `coding-edit.png` | 表内编辑、保存／取消和撤销入口 |
| `materials.png` | 原材料档案、换算和供应商价格 |
| `quick-coding-mobile.png` | 移动端快捷抄码 |

## 重新生成

在 `frontend/` 启动本地前端：

```bash
npm ci
npm run dev
```

另开终端，在同一目录执行：

```bash
npm run docs:screenshots
```

脚本默认使用 macOS 的 Google Chrome。其他平台通过 `CHROME_PATH` 指定浏览器；前端地址可通过 `TEST_BASE_URL` 指定，但只允许本机地址。无需启动后端或填写账号密码。

截图日期取当前上海日期。重新生成后检查画面和 README 描述，再一起提交。请勿使用生产截图替换这些演示图片。
