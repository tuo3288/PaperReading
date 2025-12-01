"""
审核者Agent - 负责选择问题、核实答案、整合报告
"""

import logging
import re
from typing import Dict, List
from graph.state import PaperAnalysisState
from utils.llm_client import LLMClient
from agents.prompts import (
    build_reviewer_select_questions_prompt,
    build_reviewer_verify_prompt,
    build_reviewer_final_integration_prompt
)


logger = logging.getLogger(__name__)


def select_questions(state: PaperAnalysisState, llm_client: LLMClient) -> Dict:
    """
    选择N个重要问题（根据配置中的 num_questions）

    Args:
        state: 当前状态
        llm_client: LLM客户端

    Returns:
        Dict: 更新后的状态字段
    """
    logger.info("Reviewer: Selecting questions...")

    paper_structure = state['paper_structure']
    num_questions = state.get('total_questions', 3)  # 从状态中获取配置的问题数量

    # 构建prompt
    prompt = build_reviewer_select_questions_prompt(paper_structure, num_questions)

    # 调用LLM
    questions_text = llm_client.call_reviewer(prompt)

    # 解析问题
    questions = parse_questions(questions_text, num_questions)

    logger.info(f"Reviewer: Selected {len(questions)} questions")

    return {
        'selected_questions': questions,
        'messages': [{
            'role': 'reviewer',
            'content': questions_text,
            'round': 0,
            'question_id': 0
        }]
    }


def verify_answer(
    state: PaperAnalysisState,
    llm_client: LLMClient,
    question: str,
    answer: str,
    question_id: int
) -> Dict:
    """
    核实分析者的答案

    Args:
        state: 当前状态
        llm_client: LLM客户端
        question: 问题
        answer: 分析者的答案
        question_id: 问题编号

    Returns:
        Dict: 包含核实结果的字典
    """
    logger.info(f"Reviewer: Verifying answer for question {question_id}...")

    paper_content = state['paper_content']

    # 构建prompt
    prompt = build_reviewer_verify_prompt(question, answer, paper_content)

    # 调用LLM
    verification_result = llm_client.call_reviewer(prompt)

    # 解析结果
    is_accurate, needs_followup, followup_question = parse_verification_result(verification_result)

    logger.info(f"Reviewer: Verification complete. Accurate: {is_accurate}, Needs followup: {needs_followup}")

    return {
        'verification_result': verification_result,
        'is_accurate': is_accurate,
        'needs_followup': needs_followup,
        'followup_question': followup_question,
        'messages': [{
            'role': 'reviewer',
            'content': verification_result,
            'round': state['current_round'],
            'question_id': question_id
        }]
    }


def integrate_final_report(state: PaperAnalysisState, llm_client: LLMClient) -> Dict:
    """
    整合最终报告

    Args:
        state: 当前状态
        llm_client: LLM客户端

    Returns:
        Dict: 更新后的状态字段
    """
    logger.info("Reviewer: Integrating final report...")

    # 格式化对话历史
    qa_history = format_qa_history(state['messages'])

    # 构建prompt
    prompt = build_reviewer_final_integration_prompt(qa_history)

    # 读取配置，决定使用哪个模型
    config = state.get('config', {})
    workflow_config = config.get('workflow', {})
    integration_model = workflow_config.get('final_integration_model', 'reviewer')

    # 验证配置值
    if integration_model not in ['reviewer', 'analyzer']:
        logger.warning(f"Invalid final_integration_model: {integration_model}, defaulting to 'reviewer'")
        integration_model = 'reviewer'

    # 根据配置选择模型
    if integration_model == 'analyzer':
        logger.info("🔬 Using strong model (analyzer) for final integration - deep analysis mode")
        print("🔬 使用强模型整合报告（深度分析模式）...")
        # 使用强模型，temperature 稍高以获得更好的创造性
        final_report = llm_client.call_analyzer(prompt, temperature=0.3)
    else:
        logger.info("⚡ Using fast model (reviewer) for final integration - quick mode")
        print("⚡ 使用快速模型整合报告（快速生成模式）...")
        # 使用快速模型
        final_report = llm_client.call_reviewer(prompt)

    logger.info(f"Reviewer: Final report generated. Length: {len(final_report)}")

    import time
    return {
        'final_report': final_report,
        'end_time': time.time()
    }


# ==================== 辅助函数 ====================

def parse_questions(questions_text: str, num_questions: int = 3) -> List[str]:
    """从LLM输出中解析问题列表

    Args:
        questions_text: LLM返回的问题文本
        num_questions: 期望的问题数量

    Returns:
        List[str]: 解析出的问题列表
    """
    questions = []

    # 尝试匹配"问题1: ...", "问题2: ..."格式
    pattern = r'问题\d+[:：]\s*(.+?)(?=\n问题\d+[:：]|\Z)'
    matches = re.findall(pattern, questions_text, re.DOTALL)

    if matches:
        questions = [q.strip() for q in matches]
    else:
        # 备选方案：按行分割
        lines = [line.strip() for line in questions_text.split('\n') if line.strip()]
        questions = [line for line in lines if len(line) > 10]  # 过滤太短的行

    return questions[:num_questions]  # 取前N个（N由配置决定）


def parse_verification_result(verification_text: str) -> tuple:
    """
    解析核实结果

    Returns:
        tuple: (is_accurate, needs_followup, followup_question)
    """
    # 默认值
    is_accurate = True
    needs_followup = False
    followup_question = ""

    # 判断准确性
    if '不准确' in verification_text or '部分准确' in verification_text:
        is_accurate = False

    # 判断是否需要追问
    if '需要追问：是' in verification_text or '是否需要追问：是' in verification_text:
        needs_followup = True

        # 提取追问内容
        followup_pattern = r'追问内容[:：]\s*(.+?)(?=\n|$)'
        match = re.search(followup_pattern, verification_text, re.DOTALL)
        if match:
            followup_question = match.group(1).strip()

    return is_accurate, needs_followup, followup_question


def format_qa_history(messages: List[Dict]) -> str:
    """格式化对话历史"""
    formatted = "# 对话记录\n\n"

    # 按问题分组
    for i in range(0, len(messages), 2):
        if i + 1 < len(messages):
            question_msg = messages[i]
            answer_msg = messages[i + 1]

            formatted += f"## 问题 {question_msg['question_id']}\n\n"
            formatted += f"**问题**：{question_msg['content']}\n\n"
            formatted += f"**回答**：{answer_msg['content']}\n\n"
            formatted += "---\n\n"

    return formatted
