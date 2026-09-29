"""Streamlit interface for the homework code-generation agent."""
from datetime import datetime
import json

import streamlit as st

from agent import AgentError, CodeGenerator
from config import ConfigurationError, load_settings

st.set_page_config(page_title="Codegen · 代码生成助手", page_icon="⌘", layout="wide")
st.markdown("""<style>
.block-container {padding-top: 2.5rem; max-width: 1440px;}
h1 {letter-spacing: -0.035em;}
div[data-testid="stCode"] {border: 1px solid #dfe5ed; border-radius: 10px;}
div[data-testid="stMetric"] {padding: 0.4rem 0;}
footer {visibility: hidden;}
</style>""", unsafe_allow_html=True)

st.session_state.setdefault("turns", [])
st.session_state.setdefault("last_error", "")
st.session_state.setdefault("failed_events", [])

try:
    settings = load_settings()
except ConfigurationError as exc:
    st.title("代码生成助手")
    st.error(str(exc))
    st.info("复制 .env.example 为 .env，填写 DeepSeek 密钥或密钥文件路径后刷新页面。")
    st.stop()

with st.sidebar:
    st.markdown("### CODEGEN")
    st.caption("Homework 01 · 代码生成 Agent")
    st.divider()
    st.markdown("**当前模型**")
    st.code(settings.model, language=None)
    st.caption("DeepSeek 官方 API · Python 3.14")
    st.markdown("**工作流程**")
    st.write("1. 理解需求并生成代码\n2. 调用工具检查语法\n3. 根据错误修正\n4. 保存并交付文件")
    st.divider()
    st.caption("最近 3 次成功结果会作为上下文，支持继续修改。")
    if st.button("开始新对话", use_container_width=True):
        st.session_state.turns = []
        st.session_state.last_error = ""
        st.session_state.failed_events = []
        st.session_state.request = ""
        st.session_state.example = "选择示例"
        st.rerun()
    st.caption("输出目录：项目下的 generated 文件夹")

st.caption("从一个需求，得到一份可读的 Python 脚本")
st.title("代码生成助手")
st.write("描述功能和输入输出，助手会生成代码、调用检查工具，并根据检查结果修正。")
st.divider()

EXAMPLES = {
    "选择示例": "",
    "成绩统计": "写一个 Python 函数 analyze_scores(scores)，返回平均分、最高分、最低分及及格人数。成绩范围 0–100，空列表和非法输入要给出清楚错误。附一个运行示例。",
    "CSV 数据汇总": "写一个 Python 命令行脚本，读取指定 CSV 文件，把 amount 列中的数字相加。使用标准库，处理文件不存在、缺少列、空值和非法数字。",
    "密码生成器": "使用 Python 标准库 secrets 写一个随机密码生成器，支持指定长度，包含大小写字母、数字和符号，验证长度范围，并提供命令行使用方法。",
}


def choose_example():
    selected = st.session_state.example
    if selected != "选择示例":
        st.session_state.request = EXAMPLES[selected]


left, right = st.columns([0.95, 1.55], gap="large")
with left:
    st.subheader("你想实现什么？")
    st.selectbox("从示例开始", list(EXAMPLES), key="example", on_change=choose_example)
    with st.form("generation_form"):
        prompt = st.text_area("代码需求", height=220, max_chars=6000, key="request",
                              placeholder="例如：写一个读取 CSV 并计算平均值的脚本，处理缺失数据……")
        submitted = st.form_submit_button("生成并检查", type="primary", use_container_width=True)
    st.caption("可继续输入“在上一次代码中增加……”来修改。每次交付一个 Python 文件。")
    if submitted:
        st.session_state.last_error = ""
        st.session_state.failed_events = []
        with st.status("正在生成并检查代码……", expanded=True) as status:
            current_events = []

            def show_event(event):
                current_events.append(event)
                st.write(event["text"])

            try:
                with CodeGenerator(settings) as generator:
                    result = generator.run(prompt, st.session_state.turns, show_event)
                turn = {"prompt": prompt.strip(), "result": result.to_dict(),
                        "created_at": datetime.now().strftime("%H:%M:%S")}
                st.session_state.turns = (st.session_state.turns + [turn])[-6:]
                status.update(label="代码已通过语法检查并保存", state="complete", expanded=False)
            except AgentError as exc:
                st.session_state.last_error = str(exc)
                st.session_state.failed_events = current_events
                status.update(label="本次生成未完成", state="error", expanded=True)
            except Exception:
                # Never display raw API errors, request headers or configuration values.
                st.session_state.last_error = "发生未预期的错误。本次结果未加入对话，请重新尝试。"
                st.session_state.failed_events = current_events
                status.update(label="本次生成未完成", state="error", expanded=True)
    if st.session_state.last_error:
        st.error(st.session_state.last_error)
    st.info("检查工具只解析和编译代码，不运行生成的脚本。语法通过后，仍需按运行说明验证功能。")

with right:
    st.subheader("生成结果")
    turns = st.session_state.turns
    if not turns:
        st.markdown("输入你的需求，然后点击 **生成并检查**。")
        st.code("# 生成的 Python 代码会显示在这里\n# 工具记录会保留每次检查和修正的结果", language="python")
        st.caption("建议写清楚：功能、输入格式、输出格式，以及需要处理的异常情况。")
    else:
        latest = turns[-1]
        if len(turns) > 1:
            selection = st.selectbox("查看结果", list(reversed(range(len(turns)))),
                                     format_func=lambda i: f"{turns[i]['created_at']} · {turns[i]['prompt'][:40]}",
                                     key=f"result_selection_{len(turns)}_{turns[-1]['created_at']}")
            latest = turns[selection]
        result = latest["result"]
        artifact = result["artifact"]
        col1, col2, col3 = st.columns(3)
        col1.metric("代码行数", artifact["lines"])
        col2.metric("模型轮数", result["rounds"])
        col3.metric("耗时", f"{result['seconds']:.1f} 秒")
        st.caption(f"需求：{latest['prompt']}")
        code_tab, guide_tab, trace_tab = st.tabs(["代码", "运行说明", "工具记录"])
        with code_tab:
            st.success("语法和编译检查通过")
            st.code(artifact["code"], language="python", line_numbers=True)
            st.download_button("下载 Python 文件", artifact["code"].encode("utf-8"),
                               file_name=artifact["filename"], mime="text/x-python", use_container_width=True)
            st.caption(f"本机文件：{artifact['path']}")
        with guide_tab:
            st.markdown(artifact["explanation"])
            st.caption("生成代码未在本应用中执行，请在理解代码后自行运行并验证结果。")
        with trace_tab:
            for event in result["events"]:
                st.write(event["text"])
            st.caption(f"模型：{result['model']} · 本次总 Token：{result['total_tokens']}")
            report = {"prompt": latest["prompt"], "model": result["model"],
                      "rounds": result["rounds"], "total_tokens": result["total_tokens"],
                      "seconds": result["seconds"], "sha256": artifact["sha256"],
                      "filename": artifact["filename"], "events": result["events"]}
            st.download_button("下载检查记录", json.dumps(report, ensure_ascii=False, indent=2),
                               file_name="check_report.json", mime="application/json")
