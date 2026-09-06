import streamlit as st
from iterative_workflow import app

st.title("🚀 LinkedIn Post Generator")

topic = st.text_input(
    "Enter a topic for your LinkedIn post",
    placeholder="e.g. Generative AI trends in 2026"
)
if st.button("✨ Generate Post"):
    if topic:
        initial_state = {
            "topic": topic,
            "messages": [],
            "draft": "",
            "review_feedback": "",
            "is_approved": False,
            "attempt": 0,
        }

        with st.status("🚀 Generating your LinkedIn post...", expanded=True) as status:
            st.write("✍️ Writing and reviewing your post...")

            final_state = app.invoke(initial_state)

            status.update(
                label="✅ Post generation complete!",
                state="complete",
                expanded=False
            )

        st.subheader("Generated LinkedIn Post")
        st.write(final_state["draft"])

        st.divider()

        col1, col2 = st.columns(2)

        col1.metric(
            "Review Status",
            "✅ Approved" if final_state["is_approved"] else "⚠️ Max Attempts"
        )

        col2.metric(
            "Review Attempts",
            final_state["attempt"]
        )

        st.download_button(
          label="📥 Download Post",
          data=final_state["draft"],
          file_name="linkedin_post.txt",
          mime="text/plain"
)

    else:
        st.warning("Please enter a topic.")