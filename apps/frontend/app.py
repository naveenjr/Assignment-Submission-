import streamlit as st

from apps.backend.orchestrator import investigate_sync

st.set_page_config(page_title="Alarm Copilot", page_icon="🚨")
st.title("Alarm Investigation Agent")

default_question = (
    "Show active critical alarms for Boiler Feed Pump 102 and recommend immediate actions."
)

if "question" not in st.session_state:
    st.session_state.question = default_question

if "investigation_result" not in st.session_state:
    st.session_state.investigation_result = None


def clear_investigation() -> None:
    """Clear the question and the evidence from the previous investigation."""
    st.session_state.question = ""
    st.session_state.investigation_result = None


question = st.text_area(
    "Ask an alarm investigation question",
    key="question",
)

investigate_clicked, clear_clicked = st.columns([4, 1])
with investigate_clicked:
    investigate = st.button("Investigate", type="primary", use_container_width=True)
with clear_clicked:
    st.button("Clear", on_click=clear_investigation, use_container_width=True)

if investigate:
    if not question.strip():
        st.warning("Enter an investigation question before clicking Investigate.")
    else:
        with st.spinner("The LLM is selecting MCP tools and gathering evidence..."):
            try:
                st.session_state.investigation_result = investigate_sync(question)
            except Exception as exc:
                st.error(str(exc))

result = st.session_state.investigation_result
if result:
    trace = result["trace"]
    tool_names = list(dict.fromkeys(
        event["tool"] for event in trace if event.get("tool")
    ))
    document_sources = list(dict.fromkeys(
        source["source"] for source in result["sources"] if source.get("source")
    ))

    with st.sidebar:
        st.header("Investigation details")
        st.caption("Evidence used to produce the answer")
        st.metric("MCP tools used", len(tool_names))
        for tool_name in tool_names:
            st.write(f"- `{tool_name}`")

        st.metric("Documents used", len(document_sources))
        for source in document_sources:
            st.write(f"- `{source}`")

        st.divider()
        st.caption("Correlation ID")
        st.code(result["trace_id"], language="text")
        with st.expander("MCP trace", expanded=False):
            st.json(trace)
        with st.expander("Document evidence", expanded=False):
            st.json(result["sources"])

    st.subheader("Grounded answer")
    st.markdown(result["answer"])
    with st.expander("Message and tool trace"):
        st.json([
            message.model_dump() if hasattr(message, "model_dump") else str(message)
            for message in result["messages"]
        ])
