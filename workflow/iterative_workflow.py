import os
from pathlib import Path
from typing import TypedDict, Annotated

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


# --------------------------------------------------
# Environment Variables
# --------------------------------------------------

load_dotenv(Path(__file__).resolve().parent / ".env")


# --------------------------------------------------
# Tools
# --------------------------------------------------

search_tool = TavilySearch(max_results=3)
tools = [search_tool]


# --------------------------------------------------
# LLMs
# --------------------------------------------------

# Writer: Gemini
# Writer: Groq
writer_llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.7,
)

writer_llm_with_tools = writer_llm.bind_tools(tools)


# Reviewer: Groq
reviewer_llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.2
)


# --------------------------------------------------
# State
# --------------------------------------------------

class State(TypedDict):
    topic: str
    messages: Annotated[list, add_messages]
    draft: str
    review_feedback: str
    is_approved: bool
    attempt: int


# --------------------------------------------------
# Writer
# --------------------------------------------------

WRITER_SYSTEM_PROMPT = (
    "You are an expert LinkedIn content writer. Your job is to write "
    "engaging, professional LinkedIn posts about the given topic. "
    "If the topic requires up-to-date information, statistics, or "
    "current trends, use the web search tool to gather fresh context "
    "before writing. If you have already received feedback on a "
    "previous draft, carefully address every point in the new draft. "
    "Rules for good LinkedIn posts: strong hook in the first line, "
    "1 clear takeaway, easy to skim (short paragraphs), around "
    "150–200 words, ends with a question or call-to-action to invite "
    "engagement. Do not use hashtags."
)


def writer_node(state: State) -> dict:
    topic = state["topic"]
    previous_feedback = state["review_feedback"]

    if not previous_feedback:
        user_message = (
            f"Write a LinkedIn post on this topic: {topic}. "
            "If you need current information, statistics, or trends, "
            "search the web first."
        )
    else:
        user_message = (
            f"Your previous draft on '{topic}' was rejected. "
            f"Here is the reviewer's feedback:\n\n"
            f"{previous_feedback}\n\n"
            "Write a new, improved draft that fixes every issue "
            "mentioned in the feedback. Do not repeat the same mistakes."
        )

    messages = [
        ("system", WRITER_SYSTEM_PROMPT),
        *state["messages"],
        ("human", user_message),
    ]

    response = writer_llm_with_tools.invoke(messages)

    return {
        "messages": [
            ("human", user_message),
            response,
        ]
    }


# Tool execution node
tool_node = ToolNode(tools)


# --------------------------------------------------
# Extract Draft
# --------------------------------------------------

def extract_draft_node(state: State) -> dict:
    """Extract only the final text from the writer's response."""

    last_message = state["messages"][-1]

    draft = last_message.content

    if isinstance(draft, list):
        text_parts = []

        for item in draft:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))

        draft = "\n".join(text_parts)

    draft = str(draft).strip()

    print(f"\n\ngenerated post:\n{draft}\n")

    return {
        "draft": draft
    }


# --------------------------------------------------
# Reviewer
# --------------------------------------------------

REVIEWER_SYSTEM_PROMPT = (
    "You are a strict LinkedIn content reviewer. You judge whether a "
    "post is publish-ready. Evaluate against these criteria:\n"
    "1. Strong hook in the first line\n"
    "2. One clear, valuable takeaway\n"
    "3. Easy to skim — uses short paragraphs\n"
    "4. Between 150 and 200 words. Reject if outside this range.\n"
    "5. Ends with an engaging question or CTA\n"
    "6. Professional but human tone (not corporate-robotic)\n"
    "7. No hashtags\n"
    "8. Any factual statistic or specific claim must be supported by "
    "reliable information. If a claim appears questionable or unsupported, "
    "reject the post.\n\n"
    "Respond in exactly this format:\n"
    "VERDICT: APPROVED or REJECTED\n"
    "FEEDBACK: <one short paragraph explaining why>\n\n"
    "Be strict but fair. Approve only if ALL criteria are satisfied. "
    "Reject if even one criterion is clearly missing or violated."
)
def reviewer_node(state: State) -> dict:
    """Review the draft and validate the reviewer's response."""

    draft = state["draft"]

    prompt = (
        f"Review this LinkedIn post draft:\n\n"
        f"{draft}\n\n"
        "Return exactly this format:\n"
        "VERDICT: APPROVED or REJECTED\n"
        "FEEDBACK: One short paragraph explaining your decision."
    )

    response = reviewer_llm.invoke(
        [
            ("system", REVIEWER_SYSTEM_PROMPT),
            ("human", prompt),
        ]
    )

    review_text = response.content.strip()

    # Extract the verdict.
    verdict_line = next(
        (
            line.strip()
            for line in review_text.splitlines()
            if line.strip().upper().startswith("VERDICT:")
        ),
        "",
    )

    verdict_value = verdict_line.partition(":")[2].strip().upper()

    # Extract feedback.
    feedback_line = next(
        (
            line.strip()
            for line in review_text.splitlines()
            if line.strip().upper().startswith("FEEDBACK:")
        ),
        "",
    )

    feedback = feedback_line.partition(":")[2].strip()

    # Validate the response before accepting the verdict.
    valid_verdict = verdict_value in {"APPROVED", "REJECTED"}

    if not valid_verdict or not feedback:
        is_approved = False
        feedback = (
            "The reviewer returned an invalid response format. "
            "Please review the draft again."
        )
    else:
        is_approved = verdict_value == "APPROVED"

    verdict = "APPROVED" if is_approved else "REJECTED"

    print(f"[Verdict: {verdict}]")
    print(f"[Feedback: {feedback}]")

    return {
        "review_feedback": feedback,
        "is_approved": is_approved,
        "attempt": state.get("attempt", 0) + 1,
    }

# --------------------------------------------------
# Routing: Continue or Stop
# --------------------------------------------------

# Routing: Tool or Draft
def should_use_tool(state: State):
    last_message = state["messages"][-1]

    if getattr(last_message, "tool_calls", None):
        return "tools"

    return "extract_draft"

def should_stop_looping(state: State):
    if state["is_approved"]:
        print("Post has been approved.\n")
        return END

    if state["attempt"] >= 3:
        print("Reached maximum attempts.")
        return END

    return "writer"


# --------------------------------------------------
# Build Graph
# --------------------------------------------------

graph = StateGraph(State)

graph.add_node("writer", writer_node)
graph.add_node("tools", tool_node)
graph.add_node("extract_draft", extract_draft_node)
graph.add_node("reviewer", reviewer_node)


graph.add_edge(START, "writer")


graph.add_conditional_edges(
    "writer",
    should_use_tool,
)


graph.add_edge("tools", "writer")


graph.add_edge("extract_draft", "reviewer")


graph.add_conditional_edges(
    "reviewer",
    should_stop_looping,
)


app = graph.compile()


# --------------------------------------------------
# Terminal Execution
# --------------------------------------------------

if __name__ == "__main__":

    print("=" * 55)
    print("Welcome to the LinkedIn Post Generator")
    print("=" * 55)

    print(
        "\nThis tool will draft a LinkedIn post for you, review it "
        "itself, and iterate until it's publish-ready."
    )

    print("=" * 55)

    topic = input(
        "\nWhat topic do you want a LinkedIn post about?\n> "
    ).strip()

    if not topic:
        print("\nNo topic given. Exiting.")

    else:
        print("\nStarting generation...\n")

        initial_state = {
            "topic": topic,
            "messages": [],
            "draft": "",
            "review_feedback": "",
            "is_approved": False,
            "attempt": 0,
        }

        final_state = app.invoke(initial_state)

        print("\n" + "=" * 55)
        print("FINAL LINKEDIN POST")
        print("=" * 55)

        print(final_state["draft"])

        print("=" * 55)
        print(f"Total attempts: {final_state['attempt']}")
        print(f"Approved: {final_state['is_approved']}")

