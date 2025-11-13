"""
LangGraph State Definition for Multi-Agent Paper Analysis
"""

from typing import TypedDict, List, Dict, Annotated, Sequence
import operator


class Message(TypedDict):
    """单个消息的结构"""
    role: str  # "analyzer" or "reviewer"
    content: str
    round: int  # 第几轮对话
    question_id: int  # 问题编号（0=架构,1-3=具体问题）


class QAPair(TypedDict):
    """问答对"""
    question: str
    analyzer_answer: str
    verification_result: str
    is_verified: bool
    followup_needed: bool
    followup_question: str


class PaperAnalysisState(TypedDict):
    """
    Multi-Agent论文分析的完整状态
    """
    # ========== 输入 ==========
    paper_path: str  # PDF文件路径
    paper_content: str  # 论文全文（带页码标记）

    # ========== 第0轮：架构分析 ==========
    paper_structure: str  # 分析者生成的论文架构

    # ========== 问题选择 ==========
    selected_questions: List[str]  # 审核者选择的3个问题

    # ========== 对话历史 ==========
    messages: Annotated[Sequence[Message], operator.add]  # 所有对话消息
    qa_pairs: List[QAPair]  # 结构化的问答对

    # ========== 核实结果 ==========
    verification_results: List[Dict]  # 每个回答的核实结果

    # ========== 流程控制 ==========
    current_question_id: int  # 当前问题编号（0=架构,1-3=问题）
    current_round: int  # 当前轮次
    total_questions: int  # 总问题数（配置）
    max_followups: int  # 每个问题最多追问次数

    # ========== 输出 ==========
    final_report: str  # 最终报告
    intermediate_outputs: Dict[str, str]  # 中间输出（用于调试）

    # ========== 元数据 ==========
    config: Dict  # 配置信息
    start_time: float  # 开始时间
    end_time: float  # 结束时间


def create_initial_state(paper_path: str, paper_content: str, config: Dict) -> PaperAnalysisState:
    """创建初始状态"""
    import time

    return PaperAnalysisState(
        # 输入
        paper_path=paper_path,
        paper_content=paper_content,

        # 架构
        paper_structure="",

        # 问题
        selected_questions=[],

        # 对话
        messages=[],
        qa_pairs=[],

        # 核实
        verification_results=[],

        # 流程控制
        current_question_id=0,
        current_round=0,
        total_questions=config.get('workflow', {}).get('num_questions', 3),
        max_followups=config.get('workflow', {}).get('max_followup_per_question', 2),

        # 输出
        final_report="",
        intermediate_outputs={},

        # 元数据
        config=config,
        start_time=time.time(),
        end_time=0.0
    )
