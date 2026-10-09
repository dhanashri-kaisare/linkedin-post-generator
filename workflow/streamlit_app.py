import streamlit as st
from iterative_workflow import app

st.set_page_config(
    page_title="LinkedIn Post Generator",
    page_icon="🚀",
    layout="centered",
)

st.title("🚀 LinkedIn Post Generator")
st.write("Generate, review, and refine a LinkedIn post using AI.")

topic = st.text_input(
    "Enter a topic for your LinkedIn post",
    placeholder="e.g. Generative AI trends in 2026",
)

if st.button("✨ Generate Post", type="primary"):
    if not topic.strip():
        st.warning("Please enter a topic.")
    else:
        initial_state = {
            "topic": topic.strip(),
            "messages": [],
            "draft": "",
            "review_feedback": "",
            "is_approved": False,
            "attempt": 0,
        }

        try:
            with st.spinner("✍️ Writing and reviewing your post..."):
                final_state = app.invoke(initial_state)

            st.subheader("Generated LinkedIn Post")
            st.markdown(final_state.get("draft", ""))

            st.divider()

            col1, col2 = st.columns(2)

            approved = final_state.get("is_approved", False)

            col1.metric(
                "Review Status",
                "✅ Approved" if approved else "⚠️ Not approved",
            )

            col2.metric(
                "Review Attempts",
                final_state.get("attempt", 0),
            )

            if final_state.get("review_feedback"):
                with st.expander("Latest reviewer feedback"):
                    st.write(final_state["review_feedback"])

            if final_state.get("draft"):
                st.download_button(
                    label="📥 Download Post",
                    data=final_state["draft"],
                    file_name="linkedin_post.txt",
                    mime="text/plain",
                )

            if not approved:
                st.warning(
                    "The post was not approved within the allowed attempts. "
                    "Review the feedback before publishing."
                )

        except Exception:
            st.error(
                "Post generation failed. Check your API configuration "
                "and terminal logs, then try again."
            )
            st.exception(Exception("See the terminal for the original error."))