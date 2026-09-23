import streamlit as st

from apps.backend.orchestrator import investigate_sync

st.set_page_config(page_title="Alarm Copilot", page_icon="🚨")
st.title("Alarm Investigation Agent")
#st.caption("LangGraph + LLM tool calling + MCP + local RAG")

question = st.text_area(
    "Ask an alarm investigation question",
    "Show active critical alarms for Boiler Feed Pump 102 and recommend immediate actions.",
)

if st.button("Investigate", type="primary"):
    with st.spinner("The LLM is selecting MCP tools and gathering evidence..."):
        try:
            result = investigate_sync(question)
        except Exception as exc:
            st.error(str(exc))
        else:
            st.subheader("Grounded answer")
            st.markdown(result["answer"])
            st.subheader("Document sources")
            st.json(result["sources"])
            with st.expander("Message and tool trace"):
                st.json([
                    message.model_dump() if hasattr(message, "model_dump") else str(message)
                    for message in result["messages"]
                ])
