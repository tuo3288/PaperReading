# 快速入门指南

本指南将帮助您在 5 分钟内开始使用论文分析多代理系统。

---

## 第一步：环境安装

选择一种方式安装依赖（推荐使用 Conda）：

### 方式1: Conda（推荐）

```bash
# 创建并激活环境
conda env create -f environment.yml
conda activate paper-reading
```

### 方式2: uv（最快）

```bash
# 安装 uv
pip install uv

# 安装依赖
uv pip install -r requirements.txt
```

### 方式3: pip（传统方式）

```bash
pip install -r requirements.txt
```

详细环境配置说明请参考 [ENVIRONMENT.md](ENVIRONMENT.md)

---

## 第二步：配置 API

1. 复制配置示例文件：

```bash
cp config.example.yaml config.yaml
```

2. 编辑 `config.yaml`，填写您的 API 信息：

```yaml
api:
  base_url: "https://your-api.com/v1"  # 您的 API 地址
  api_key: "your-api-key-here"         # 您的 API 密钥

models:
  analyzer: "gpt-4"           # 强模型（用于分析论文）
  reviewer: "gpt-3.5-turbo"   # 快速模型（用于审核和整合）
```

---

## 第三步：运行首次分析

准备好您的 PDF 论文文件（如 `paper.pdf`），然后运行：

```bash
python main.py paper.pdf
```

### 工作流程说明

程序将自动执行以下步骤：

1. **📄 解析 PDF 内容**
   - 提取论文文本和结构

2. **🔍 分析论文结构**
   - 分析者（Analyzer）理解论文架构和关键内容

3. **❓ 审核者选择问题**
   - 审核者（Reviewer）自动选择 3 个核心问题

4. **💬 问答循环**
   - 分析者逐个回答问题
   - 每个问题可以追问多轮，深入挖掘细节

5. **✅ 生成初版报告**
   - 审核者整合所有问答，生成结构化报告

6. **💾 自动保存检查点**
   - 保存完成状态，方便后续恢复和提问

7. **💬 用户对话模式（可选）**
   - 询问是否进入对话模式
   - 您可以就论文内容自由提问

8. **📝 重新整合笔记（如有对话）**
   - 如果您提了问题，会自动整合进最终报告

### 示例输出

```
📝 加载配置...
🚀 开始分析论文: paper.pdf
--------------------------------------------------

📋 分析论文结构...
✅ 论文结构分析完成

❓ 审核者正在选择问题...
✅ 选择了 3 个核心问题

💬 问题 1/3: 这篇论文的核心创新点是什么？
🔍 分析者正在思考...
✅ 回答完成

...

📝 保存初版报告...
✅ 报告已保存至: output/paper_analysis_20251113_143025.md

💾 保存完成状态检查点...
💾 Checkpoint saved: checkpoints/2510.19555v1/checkpoint_final_20251113_143025.json

📄 初版报告已生成，请先阅读:
   output/paper_analysis_20251113_143025.md

==================================================
是否需要进入对话模式向分析者提问? (y/n):
```

---

## 第四步：阅读生成的报告

打开生成的 Markdown 文件（位于 `output/` 目录）：

```bash
# Windows
notepad output/paper_analysis_20251113_143025.md

# Linux/Mac
cat output/paper_analysis_20251113_143025.md
```

报告包含以下结构：

```markdown
# 论文分析报告

## 研究背景 & 主要贡献
- 背景介绍
- 核心创新点

## 主要内容详解
### 1. 创新点1的详细分析
...

### 2. 创新点2的详细分析
...

## 总结
- 主要发现
- 潜在影响
```

---

## 进阶功能

### 1. 用户对话模式

阅读初版报告后，您可以进入对话模式向分析者提问：

```
==================================================
是否需要进入对话模式向分析者提问? (y/n): y

💬 用户对话模式
==================================================
您可以就论文内容向分析者提问。
输入 '结束' 或 'exit' 退出对话模式。

👤 您的问题: 论文中的实验设计有什么特点？

🤖 分析者正在思考...

🤖 分析者: 根据论文内容，实验设计有以下几个特点：
1. ...
2. ...

--------------------------------------------------

👤 您的问题: exit

✅ 退出对话模式

🔄 重新整合笔记（包含您的对话内容）...
✅ 笔记重新整合完成!

🎉 完成！最终报告已生成: output/paper_analysis_20251113_143156.md
```

**提示**：
- 对话内容会自动整合进最终报告
- 分析者可以看到已生成的笔记内容，回答更准确
- 输入 `exit`、`quit`、`结束` 或 `q` 退出对话

### 2. 从检查点恢复

如果分析过程中断，或者您想从已完成的分析继续提问：

```bash
# 自动检测并选择检查点
python main.py paper.pdf
```

程序会显示可用的检查点列表：

```
📁 发现以下检查点:

编号     保存时间                 进度                对话数    状态
----------------------------------------------------------------------
1      2025-11-13 14:30:25    已完成               15       ✅ 已完成
2      2025-11-13 14:25:10    2/3 问题             10
3      2025-11-13 14:20:05    1/3 问题              5

请选择检查点 (1-3) 或 0 重新开始: 1
```

**选择说明**：
- 选择 `1-3`：从对应的检查点恢复
- 选择 `0`：忽略检查点，从头开始新的分析
- 标记为 "✅ 已完成" 的检查点包含完整报告，恢复后会直接进入对话模式

**或者指定具体的检查点文件**：

```bash
python main.py paper.pdf --checkpoint checkpoints/2510.19555v1/checkpoint_final_20251113_143025.json
```

### 3. 提高报告质量

#### 方法1: 使用强模型整合报告

默认情况下，最终报告由快速模型（reviewer）整合。您可以改用强模型获得更高质量：

编辑 `config.yaml`：

```yaml
workflow:
  final_integration_model: "analyzer"  # 改为 analyzer（强模型）
```

然后运行：

```bash
python main.py paper.pdf
```

**权衡**：
- 优点：报告质量更高，逻辑性更强
- 缺点：耗时更长，成本更高

#### 方法2: 增加提问数量

默认审核者会选择 3 个问题。您可以增加到 5 个：

编辑 `config.yaml`：

```yaml
workflow:
  num_questions: 5  # 从 3 增加到 5
```

**权衡**：
- 优点：覆盖更全面
- 缺点：耗时更长

#### 方法3: 使用用户对话模式

自动分析完成后，进入对话模式针对性补充提问：

```
是否需要进入对话模式向分析者提问? (y/n): y

👤 您的问题: 论文的局限性是什么？
👤 您的问题: 实验结果是否具有统计显著性？
```

对话内容会自动整合进最终报告。

### 4. 清理缓存

如果检查点和输出文件太多，可以一键清空：

```bash
python main.py --reset
```

程序会询问确认：

```
⚠️  警告: 即将清空所有输出和检查点目录！
这将删除:
  - output/ 目录下的所有分析报告
  - checkpoints/ 目录下的所有检查点文件

确认清空? (yes/no): yes

✅ 清空完成!
   删除文件: 156 个
   释放空间: 3.45 MB
```

**注意**：此操作不可逆，请谨慎使用！

### 5. 自动清理管理

不想手动清理？可以配置自动清理策略。

编辑 `config.yaml`：

```yaml
checkpoint_management:
  auto_cleanup: true                # 启用自动清理
  max_checkpoint_size_mb: 100       # 总大小超过 100MB 时清理
  max_checkpoint_files: 50          # 总文件数超过 50 时清理
  max_checkpoint_age_days: 7        # 删除 7 天前的检查点
  keep_per_paper: 2                 # 每篇论文只保留最新 2 个检查点
  keep_completed: true              # 保留已完成的检查点
```

程序启动时会自动检查并清理：

```
🧹 自动清理: 删除了 23 个检查点文件，释放 12.34 MB
```

---

## 命令行参数速查

```bash
# 基础用法
python main.py paper.pdf

# 从最新检查点恢复
python main.py paper.pdf --resume

# 从指定检查点恢复
python main.py paper.pdf --checkpoint checkpoints/2510.19555v1/checkpoint_final_xxx.json

# 使用自定义配置文件
python main.py paper.pdf --config my_config.yaml

# 指定输出目录
python main.py paper.pdf --output-dir my_output

# 清空所有缓存
python main.py --reset
```

---

## 常见问题

### Q1: 如何知道论文是否是 arXiv 论文？

程序会自动识别：
- **文件名包含 arXiv ID**（如 `2510.19555v1.pdf`）
- **PDF 内容包含 arXiv ID**（如 "arXiv:2510.19555v1"）

检查点会自动保存到对应目录：
- arXiv 论文：`checkpoints/2510.19555v1/`
- 其他论文：`checkpoints/custom_1/`, `checkpoints/custom_2/`, ...

### Q2: 如何查看检查点的可读版本？

每个检查点都会同时保存两个文件：
- `checkpoint_q1a0_xxx.json` - 机器可读（用于恢复）
- `readable_q1a0_xxx.md` - 人类可读（Markdown 格式）

直接打开 `.md` 文件即可查看：

```bash
cat checkpoints/2510.19555v1/readable_final_20251113_143025.md
```

### Q3: 如何只生成报告，不进入对话模式？

编辑 `config.yaml`：

```yaml
workflow:
  enable_user_qa: false  # 禁用用户对话模式
```

或者运行时直接选择 `n`：

```
是否需要进入对话模式向分析者提问? (y/n): n
```

### Q4: API 调用失败怎么办？

程序内置了自动重试机制（默认 5 次）。如果仍然失败：

1. 检查 API 配置：`config.yaml` 中的 `base_url` 和 `api_key`
2. 检查网络连接
3. 查看日志文件：`paper_analysis.log`

您可以调整重试次数：

```yaml
api:
  max_retries: 10  # 增加到 10 次
```

### Q5: 如何分析多篇论文？

依次运行即可：

```bash
python main.py paper1.pdf
python main.py paper2.pdf
python main.py paper3.pdf
```

检查点会自动按论文分类，互不干扰。

---

## 最佳实践

### 1. 首次使用流程

```bash
# 1. 安装环境
conda env create -f environment.yml
conda activate paper-reading

# 2. 配置 API
cp config.example.yaml config.yaml
# 编辑 config.yaml

# 3. 运行分析
python main.py paper.pdf

# 4. 阅读初版报告
cat output/paper_analysis_xxx.md

# 5. 进入对话模式（可选）
# 在提示时选择 y

# 6. 查看最终报告
cat output/paper_analysis_xxx.md
```

### 2. 中断后恢复流程

```bash
# 程序会自动检测检查点
python main.py paper.pdf

# 选择最新的检查点继续
# 或选择 0 重新开始
```

### 3. 提高质量的推荐配置

```yaml
# config.yaml
models:
  analyzer: "gpt-4"              # 使用最强模型
  reviewer: "gpt-3.5-turbo"      # 快速模型即可

workflow:
  num_questions: 5                      # 增加问题数
  final_integration_model: "analyzer"   # 强模型整合
  enable_user_qa: true                  # 启用对话模式

checkpoint_management:
  auto_cleanup: true
  max_checkpoint_size_mb: 100
  keep_per_paper: 3                     # 保留最近 3 个检查点
```

### 4. 快速分析的推荐配置

```yaml
# config.yaml
models:
  analyzer: "gpt-3.5-turbo"     # 使用快速模型
  reviewer: "gpt-3.5-turbo"

workflow:
  num_questions: 3                      # 默认 3 个问题
  final_integration_model: "reviewer"   # 快速整合
  enable_user_qa: false                 # 跳过对话模式
```

---

## 下一步

- 查看完整文档：[README.md](README.md)
- 查看环境配置：[ENVIRONMENT.md](ENVIRONMENT.md)
- 查看配置示例：[config.example.yaml](config.example.yaml)

---

## 技术支持

遇到问题？
1. 查看日志文件：`paper_analysis.log`
2. 查看常见问题：[README.md#常见问题](README.md#❓-常见问题)
3. 提交 Issue（如果是 GitHub 项目）

**祝您使用愉快！**
