from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage
from langgraph.graph import END

import workflow.iterative_workflow as workflow


def make_state(**overrides):
    state = {
        "topic": "Python",
        "messages": [],
        "draft": "Python is useful for automation.",
        "review_feedback": "",
        "is_approved": False,
        "attempt": 0,
    }
    state.update(overrides)
    return state


def run_reviewer_test(state, response_text):
    mock_response = Mock()
    mock_response.content = response_text

    mock_model = Mock()
    mock_model.invoke.return_value = mock_response

    with patch(
        "workflow.iterative_workflow.reviewer_llm",
        new=mock_model,
    ):
        return workflow.reviewer_node(state)


def test_reviewer_approves_valid_response():
    result = run_reviewer_test(
        make_state(),
        "VERDICT: APPROVED\n"
        "FEEDBACK: The post is clear and well structured.",
    )

    assert result["is_approved"] is True
    assert result["attempt"] == 1
    assert "clear and well structured" in result["review_feedback"]


def test_reviewer_rejects_response():
    result = run_reviewer_test(
        make_state(draft="Python guarantees everyone a job."),
        "VERDICT: REJECTED\n"
        "FEEDBACK: Please remove unsupported claims.",
    )

    assert result["is_approved"] is False
    assert result["attempt"] == 1
    assert "unsupported claims" in result["review_feedback"]


def test_reviewer_handles_invalid_response():
    result = run_reviewer_test(
        make_state(),
        "This response does not follow the expected format.",
    )

    assert result["is_approved"] is False
    assert result["attempt"] == 1
    assert "invalid response format" in result["review_feedback"]


def test_should_use_tools_when_tool_call_exists():
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search",
                "args": {"query": "Python"},
                "id": "call_1",
                "type": "tool_call",
            }
        ],
    )

    assert workflow.should_use_tool(
        make_state(messages=[message])
    ) == "tools"


def test_should_extract_draft_without_tool_call():
    message = AIMessage(content="Here is the generated post.")

    assert workflow.should_use_tool(
        make_state(messages=[message])
    ) == "extract_draft"


def test_workflow_stops_when_approved():
    assert workflow.should_stop_looping(
        make_state(is_approved=True, attempt=1)
    ) == END


def test_workflow_stops_after_three_attempts():
    assert workflow.should_stop_looping(
        make_state(is_approved=False, attempt=3)
    ) == END


def test_workflow_retries_when_not_approved():
    assert workflow.should_stop_looping(
        make_state(is_approved=False, attempt=1)
    ) == "writer"

