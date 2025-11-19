"""
Prompt模板 - 简洁版，避免过多格式要求减少幻觉
"""


# ==================== 分析者Prompts ====================

ANALYZER_STRUCTURE_PROMPT = """请阅读这篇论文，总结其行文架构和主要内容。

论文内容：
{paper_content}

请简要说明：
1. 论文的章节结构
2. 每个部分的核心内容（1-2句话）

保持简洁。"""


ANALYZER_ANSWER_PROMPT = """请基于论文内容回答以下问题。如果引用论文内容，请标注页码[P3]。

论文内容：
{paper_content}

问题：{question}

请给出准确、详细的回答。公式使用typora的latex格式。"""


# ==================== 审核者Prompts ====================

REVIEWER_SELECT_QUESTIONS_PROMPT = """你是论文审稿人。根据论文架构，选择3个对科研工作者最重要的问题进行深入追问。

**重要提示：你只有3次提问机会，请提问最重要、最核心的问题！**

论文架构：
{paper_structure}

提问要求：
1. **必须从论文的具体内容出发**，不要问论文中没有涉及的内容
2. **避免无意义的问题**，例如：
   - "如何复现实验"（论文通常不包含完整复现细节）
   - "代码在哪里"（与论文内容理解无关）
   - "未来工作是什么"（过于宽泛）
3. **聚焦论文核心价值**，优先询问：
   - 论文的核心创新点和技术方法（最重要）
   - 实验设计的关键细节和主要结果
   - 方法的优势、局限性或适用场景
   - 与现有方法的本质区别

直接输出3个问题，每行一个，格式：
问题1: ...
问题2: ...
问题3: ..."""


REVIEWER_VERIFY_PROMPT = """你是严格的审稿人。请核实以下回答是否准确。

问题：{question}

回答：{answer}

论文原文：
{paper_content}

请检查：
1. 引用的页码是否存在且准确
2. 回答内容是否与原文一致
3. 是否有明显的逻辑错误或臆测

输出格式：
核实结果：准确/不准确
问题点：（如有问题，简要说明）
是否需要追问：是/否
追问内容：（如需要，简要提问）"""


REVIEWER_FINAL_INTEGRATION_PROMPT = """请整合以下对话内容，生成一份论文解读报告。

对话记录：
{qa_history}

**报告结构要求：**
1. **研究背景 & 主要贡献**（概述论文背景和核心贡献点）
2. **主要内容详解**（根据文章贡献点的重要性展开核心方法、技术细节、实验结果等，灵活组织内容，可适当分节）
3. **总结**（简要总结论文价值和适用场景）

请生成结构清晰、逻辑连贯的报告，只保留经过核实的准确信息。"""


# ==================== 用户对话模式 Prompts ====================

ANALYZER_USER_QUESTION_PROMPT = """请基于论文内容和已生成的分析报告回答用户的问题。如果引用论文内容，请标注页码[P3]。

论文内容：
{paper_content}

已生成的分析报告：
{final_report}

用户问题：{user_question}

请给出准确、详细的回答，公式使用typora的latex格式。您可以参考已有的分析报告来保持一致性。如果问题超出论文范围，请明确告知用户。"""


# ==================== Prompt构建函数 ====================

def build_analyzer_structure_prompt(paper_content: str) -> str:
    """构建架构分析prompt"""
    return ANALYZER_STRUCTURE_PROMPT.format(paper_content=paper_content)


def build_analyzer_answer_prompt(paper_content: str, question: str) -> str:
    """构建分析者回答prompt"""
    return ANALYZER_ANSWER_PROMPT.format(
        paper_content=paper_content,
        question=question
    )


def build_reviewer_select_questions_prompt(paper_structure: str) -> str:
    """构建问题选择prompt"""
    return REVIEWER_SELECT_QUESTIONS_PROMPT.format(paper_structure=paper_structure)


def build_reviewer_verify_prompt(question: str, answer: str, paper_content: str) -> str:
    """构建核实prompt"""
    return REVIEWER_VERIFY_PROMPT.format(
        question=question,
        answer=answer,
        paper_content=paper_content
    )


def build_reviewer_final_integration_prompt(qa_history: str) -> str:
    """构建最终整合prompt"""
    return REVIEWER_FINAL_INTEGRATION_PROMPT.format(qa_history=qa_history)


def build_analyzer_user_question_prompt(paper_content: str, user_question: str, final_report: str = "") -> str:
    """构建用户问题回答prompt"""
    return ANALYZER_USER_QUESTION_PROMPT.format(
        paper_content=paper_content,
        final_report=final_report if final_report else "（尚未生成）",
        user_question=user_question
    )
