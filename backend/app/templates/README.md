# 私有报告模板

Word 模板包含业务报告版式及签名图片，因此不放入公开 Git 仓库。普通页面和基础业务接口不需要这些文件；以下 Word 导出及其测试需要补齐模板：

| 文件名 | 用途 |
| --- | --- |
| `RT0017202609100003678853ea.docx` | 单瓶检验报告 |
| `inspection-regular.docx` | 默认定期检验报告 |
| `inspection-assessment.docx` | 默认安全评定报告 |
| `inspection-photo-regular.docx` | 双页封面定期检验报告 |
| `inspection-photo-assessment.docx` | 双页封面安全评定报告 |

从项目维护者获取获授权的文件，放在本目录，在构建后端镜像前完成配置。布局应与导出代码预期一致，不能仅把任意 Word 文档改成对应文件名。

`backend/scripts/build_inspection_photo_templates.py` 用于维护双页封面模板，仍依赖原始业务模板和签名资源。相关行为见 `docs/inspection-word-templates.md`。

这些文件由 `.gitignore` 排除。不要提交真实签名、客户记录或生产生成的报告。
