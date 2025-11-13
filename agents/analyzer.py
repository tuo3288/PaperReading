"""
分析者Agent - 负责分析论文并回答问题
"""

import logging
from typing import Dict
from graph.state import PaperAnalysisState
from utils.llm_client import LLMClient
from agents.prompts import (
    build_analyzer_structure_prompt,
    build_analyzer_answer_prompt,
    build_analyzer_user_question_prompt
)


logger = logging.getLogger(__name__)


def analyze_structure(state: PaperAnalysisState, llm_client: LLMClient) -> Dict:
    """
    第0轮：分析论文架构

    Args:
        state: 当前状态
        llm_client: LLM客户端

    Returns:
        Dict: 更新后的状态字段
    """
    logger.info("Analyzer: Analyzing paper structure...")

    paper_content = state['paper_content']

    # 构建prompt
    prompt = build_analyzer_structure_prompt(paper_content)

    # 调用LLM
    structure = llm_client.call_analyzer(prompt)

    logger.info(f"Analyzer: Structure analysis complete. Length: {len(structure)}")

    return {
        'paper_structure': structure,
        'messages': [{
            'role': 'analyzer',
            'content': structure,
            'round': 0,
            'question_id': 0
        }],
        'intermediate_outputs': {'structure': structure}
    }


def answer_question(
    state: PaperAnalysisState,
    llm_client: LLMClient,
    question: str,
    question_id: int
) -> Dict:
    """
    回答审核者的问题

    Args:
        state: 当前状态
        llm_client: LLM客户端
        question: 问题内容
        question_id: 问题编号

    Returns:
        Dict: 更新后的状态字段
    """
    logger.info(f"Analyzer: Answering question {question_id}...")

    paper_content = state['paper_content']

    # 构建prompt
    prompt = build_analyzer_answer_prompt(paper_content, question)

    # 调用LLM
    answer = llm_client.call_analyzer(prompt)

    logger.info(f"Analyzer: Answer complete. Length: {len(answer)}")

    return {
        'messages': [{
            'role': 'analyzer',
            'content': answer,
            'round': state['current_round'],
            'question_id': question_id
        }]
    }


def answer_user_question(
    state: PaperAnalysisState,
    llm_client: LLMClient,
    user_question: str
) -> str:
    """
    回答用户的自由提问

    Args:
        state: 当前状态
        llm_client: LLM客户端
        user_question: 用户问题

    Returns:
        str: 回答内容
    """
    logger.info(f"Analyzer: Answering user question...")

    paper_content = state['paper_content']
    final_report = state.get('final_report', '')

    # 构建prompt，包含已生成的分析报告
    prompt = build_analyzer_user_question_prompt(paper_content, user_question, final_report)

    # 调用LLM
    answer = llm_client.call_analyzer(prompt)

    logger.info(f"Analyzer: User answer complete. Length: {len(answer)}")

    return answer
