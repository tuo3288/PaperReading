"""
LangGraph工作流 - 协调分析者和审核者的对话
"""

import logging
from typing import Dict
from langgraph.graph import StateGraph, END
from graph.state import PaperAnalysisState
from utils.llm_client import LLMClient
from utils.checkpoint import save_checkpoint, save_readable_checkpoint
from agents import analyzer, reviewer


logger = logging.getLogger(__name__)


def create_workflow(config: Dict) -> StateGraph:
    """
    创建Multi-Agent工作流

    Args:
        config: 配置字典

    Returns:
        StateGraph: 编译后的工作流图
    """
    # 创建LLM客户端
    llm_client = LLMClient(config)

    # 创建StateGraph
    workflow = StateGraph(PaperAnalysisState)

    # ==================== 定义节点 ====================

    def node_analyze_structure(state: PaperAnalysisState) -> Dict:
        """节点：分析者分析论文架构"""
        return analyzer.analyze_structure(state, llm_client)

    def node_select_questions(state: PaperAnalysisState) -> Dict:
        """节点：审核者选择3个问题"""
        return reviewer.select_questions(state, llm_client)

    def node_answer_question(state: PaperAnalysisState) -> Dict:
        """节点：分析者回答当前问题"""
        current_id = state['current_question_id']
        question = state['selected_questions'][current_id - 1]  # ID从1开始，列表从0开始
        return analyzer.answer_question(state, llm_client, question, current_id)

    def node_verify_answer(state: PaperAnalysisState) -> Dict:
        """节点：审核者核实答案"""
        current_id = state['current_question_id']
        question = state['selected_questions'][current_id - 1]

        # 获取最新的analyzer回答
        analyzer_messages = [msg for msg in state['messages'] if msg['role'] == 'analyzer']
        latest_answer = analyzer_messages[-1]['content'] if analyzer_messages else ""

        return reviewer.verify_answer(state, llm_client, question, latest_answer, current_id)

    def node_integrate_report(state: PaperAnalysisState) -> Dict:
        """节点：审核者整合最终报告"""
        return reviewer.integrate_final_report(state, llm_client)

    # ==================== 添加节点到图 ====================

    workflow.add_node("analyze_structure", node_analyze_structure)
    workflow.add_node("select_questions", node_select_questions)
    workflow.add_node("answer_question", node_answer_question)
    workflow.add_node("verify_answer", node_verify_answer)
    workflow.add_node("integrate_report", node_integrate_report)

    # ==================== 定义边 ====================

    # 设置入口点
    workflow.set_entry_point("analyze_structure")

    # 架构分析 -> 选择问题
    workflow.add_edge("analyze_structure", "select_questions")

    # 选择问题 -> 回答第一个问题（需要更新current_question_id）
    def after_select_questions(state: PaperAnalysisState) -> Dict:
        """选择问题后的处理"""
        return {
            'current_question_id': 1,  # 开始第一个问题
            'current_round': 1
        }

    workflow.add_node("start_qa", after_select_questions)
    workflow.add_edge("select_questions", "start_qa")
    workflow.add_edge("start_qa", "answer_question")

    # 回答问题 -> 核实答案
    workflow.add_edge("answer_question", "verify_answer")

    # 核实答案 -> 判断下一步
    def should_continue_qa(state: PaperAnalysisState) -> str:
        """判断是否继续问答"""
        current_id = state['current_question_id']
        total_questions = state['total_questions']

        # 检查是否还有问题
        if current_id < total_questions:
            return "next_question"
        else:
            return "finish"

    def move_to_next_question(state: PaperAnalysisState) -> Dict:
        """移动到下一个问题"""
        return {
            'current_question_id': state['current_question_id'] + 1,
            'current_round': state['current_round'] + 1
        }

    workflow.add_node("next_question", move_to_next_question)

    workflow.add_conditional_edges(
        "verify_answer",
        should_continue_qa,
        {
            "next_question": "next_question",
            "finish": "integrate_report"
        }
    )

    workflow.add_edge("next_question", "answer_question")

    # 整合报告 -> 结束
    workflow.add_edge("integrate_report", END)

    # ==================== 编译图 ====================

    return workflow.compile()


def run_workflow(paper_path: str, config: Dict) -> Dict:
    """
    运行完整的workflow，并在每个关键步骤保存检查点

    Args:
        paper_path: PDF文件路径
        config: 配置字典

    Returns:
        Dict: 最终状态
    """
    logger.info(f"Starting workflow for paper: {paper_path}")

    # 解析PDF
    from utils.pdf_parser import parse_pdf
    paper_content = parse_pdf(paper_path)

    # 创建初始状态
    from graph.state import create_initial_state
    initial_state = create_initial_state(paper_path, paper_content, config)

    # 创建workflow
    app = create_workflow(config)

    # 获取检查点配置
    checkpoint_config = config.get('output', {})
    enable_checkpoints = checkpoint_config.get('enable_checkpoints', True)
    checkpoint_dir = checkpoint_config.get('checkpoint_dir', 'checkpoints')

    # 使用 stream 方法运行，在每个节点后保存检查点
    current_state = dict(initial_state)  # 创建状态副本用于累积
    final_state = None  # 初始化 final_state
    checkpoint_nodes = ['analyze_structure', 'select_questions', 'answer_question', 'verify_answer']

    try:
        for state_update in app.stream(initial_state):
            # state_update 是一个字典，键是节点名称，值是状态更新
            for node_name, node_output in state_update.items():
                logger.info(f"Completed node: {node_name}")

                # 累积状态更新
                if node_output:
                    current_state.update(node_output)

                # 如果启用了检查点，并且是关键节点，则保存
                if enable_checkpoints and node_name in checkpoint_nodes:
                    if current_state:
                        logger.info(f"💾 Saving checkpoint after {node_name}...")
                        save_checkpoint(current_state, checkpoint_dir)
                        save_readable_checkpoint(current_state, checkpoint_dir)

        # stream 完成后，current_state 就是最终状态
        final_state = current_state

    except Exception as e:
        logger.error(f"Workflow failed, attempting to save checkpoint...")
        # 尝试保存当前状态（如果有的话）
        if enable_checkpoints and current_state:
            logger.info("Saving checkpoint with partial progress...")
            save_checkpoint(current_state, checkpoint_dir)
            save_readable_checkpoint(current_state, checkpoint_dir)
        raise

    logger.info("Workflow completed successfully")

    # 保存最终检查点
    if enable_checkpoints and final_state:
        logger.info("💾 Saving final checkpoint...")
        save_checkpoint(final_state, checkpoint_dir)
        save_readable_checkpoint(final_state, checkpoint_dir)

    return final_state


def resume_workflow(checkpoint_state: Dict, config: Dict) -> Dict:
    """
    从检查点恢复并继续workflow

    Args:
        checkpoint_state: 检查点状态
        config: 当前配置字典

    Returns:
        Dict: 最终状态
    """
    paper_path = checkpoint_state.get('paper_path', '')
    logger.info(f"Resuming workflow from checkpoint for paper: {paper_path}")
    logger.info(f"Checkpoint progress: Q{checkpoint_state.get('current_question_id', 0)}/{checkpoint_state.get('total_questions', 3)}")

    # 重新解析PDF（paper_content 不在检查点中）
    from utils.pdf_parser import parse_pdf
    paper_content = parse_pdf(paper_path)

    # 创建恢复状态：合并检查点数据和新解析的内容
    from graph.state import PaperAnalysisState
    import time

    resume_state = PaperAnalysisState(
        # 从检查点恢复的数据
        paper_path=paper_path,
        paper_content=paper_content,  # 重新解析
        paper_structure=checkpoint_state.get('paper_structure', ''),
        selected_questions=checkpoint_state.get('selected_questions', []),
        messages=checkpoint_state.get('messages', []),
        qa_pairs=checkpoint_state.get('qa_pairs', []),
        verification_results=checkpoint_state.get('verification_results', []),
        current_question_id=checkpoint_state.get('current_question_id', 0),
        current_round=checkpoint_state.get('current_round', 0),
        total_questions=checkpoint_state.get('total_questions', 3),
        max_followups=config.get('workflow', {}).get('max_followup_per_question', 2),
        final_report=checkpoint_state.get('final_report', ''),
        intermediate_outputs={},
        config=config,  # 使用新配置
        start_time=checkpoint_state.get('start_time', time.time()),
        end_time=0.0
    )

    # 判断从哪里继续
    current_q_id = checkpoint_state.get('current_question_id', 0)
    total_q = checkpoint_state.get('total_questions', 3)
    has_structure = bool(checkpoint_state.get('paper_structure'))
    has_questions = bool(checkpoint_state.get('selected_questions'))

    logger.info(f"Resume point: has_structure={has_structure}, has_questions={has_questions}, current_q={current_q_id}")

    # 获取检查点配置
    checkpoint_config = config.get('output', {})
    enable_checkpoints = checkpoint_config.get('enable_checkpoints', True)
    checkpoint_dir = checkpoint_config.get('checkpoint_dir', 'checkpoints')

    # 创建workflow
    app = create_workflow(config)

    # 根据检查点状态决定继续执行的策略
    if not has_structure:
        # 如果连架构分析都没有，从头开始
        logger.info("No structure found, starting from beginning")
        final_state = app.invoke(resume_state)

    elif not has_questions:
        # 有架构但没有问题，从选择问题开始
        # 这种情况比较复杂，因为 LangGraph 需要从入口点开始
        # 简化处理：从头运行，但使用已有的架构
        logger.info("Has structure but no questions, re-running workflow with existing structure")
        final_state = app.invoke(resume_state)

    elif current_q_id >= total_q:
        # 所有问题已回答，只需生成最终报告
        logger.info("All questions answered, generating final report")
        # 直接调用 integrate_report
        from agents import reviewer
        llm_client = LLMClient(config)
        result = reviewer.integrate_final_report(resume_state, llm_client)
        final_state = {**resume_state, **result, 'end_time': time.time()}

    else:
        # 部分问题已回答，继续回答剩余问题
        logger.info(f"Resuming from question {current_q_id + 1}/{total_q}")

        # 更新 current_question_id 到下一个问题
        resume_state['current_question_id'] = current_q_id + 1
        resume_state['current_round'] = resume_state.get('current_round', 0) + 1

        # 从当前位置继续执行
        # 注意：LangGraph 会从入口点开始，但我们已经设置了正确的状态
        # 工作流会根据 current_question_id 判断要执行哪些节点
        try:
            current_state = dict(resume_state)  # 创建状态副本用于累积
            for state_update in app.stream(resume_state):
                for node_name, node_output in state_update.items():
                    logger.info(f"Completed node: {node_name}")

                    # 累积状态更新
                    if node_output:
                        current_state.update(node_output)

                    if enable_checkpoints and node_name in ['answer_question', 'verify_answer']:
                        if current_state:
                            logger.info(f"💾 Saving checkpoint after {node_name}...")
                            save_checkpoint(current_state, checkpoint_dir)
                            save_readable_checkpoint(current_state, checkpoint_dir)

            # 重新调用获取最终状态
            final_state = app.invoke(resume_state)

        except Exception as e:
            logger.error(f"Resume workflow failed: {str(e)}")
            if enable_checkpoints:
                save_checkpoint(resume_state, checkpoint_dir)
                save_readable_checkpoint(resume_state, checkpoint_dir)
            raise

    logger.info("Resume workflow completed successfully")

    # 保存最终检查点
    if enable_checkpoints and final_state:
        logger.info("💾 Saving final checkpoint after resume...")
        save_checkpoint(final_state, checkpoint_dir)
        save_readable_checkpoint(final_state, checkpoint_dir)

    return final_state
