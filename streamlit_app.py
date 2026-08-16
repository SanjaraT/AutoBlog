"""
Streamlit frontend for the LangGraph Blog Writing Agent.

Run with:
    streamlit run streamlit_app.py

Make sure the FastAPI backend is running first:
    uvicorn app.backend:api --reload --port 8000
"""

import json
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Blog Writing Agent", page_icon="📝", layout="wide")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rewrite_image_paths(markdown: str) -> str:
    """
    Generated markdown contains relative image links like
    ](images/foo.png) which only work when a viewer opens the .md file
    directly from disk. In a browser (Streamlit), these need to be real
    URLs pointing at the backend's static file mount instead.
    """
    return markdown.replace("](images/", f"]({BACKEND_URL}/images/")


def fetch_recent_runs(limit: int = 20):
    """Calls GET /runs on the backend. Returns a list of run dicts, or [] on failure."""
    try:
        resp = requests.get(f"{BACKEND_URL}/runs", params={"limit": limit}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.sidebar.error(f"Couldn't reach backend: {e}")
        return []


def fetch_run_detail(run_id: int):
    """Calls GET /runs/{run_id}. Returns the run detail dict, or None on failure."""
    try:
        resp = requests.get(f"{BACKEND_URL}/runs/{run_id}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"Couldn't fetch run {run_id}: {e}")
        return None


def parse_sse_stream(response):
    """
    Generator that parses a raw SSE (Server-Sent Events) response into
    (event_type, data_dict) tuples.

    SSE lines look like:
        event: progress
        data: {"node": "worker", "message": "Writing sections..."}
        <blank line>
    """
    event_type = None
    data_lines = []

    for raw_line in response.iter_lines(decode_unicode=True):
        if raw_line is None:
            continue
        line = raw_line.strip()

        if line == "":
            # Blank line = end of one event block
            if event_type is not None and data_lines:
                data_str = "\n".join(data_lines)
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    data = {"raw": data_str}
                yield event_type, data
            event_type = None
            data_lines = []
            continue

        if line.startswith("event:"):
            event_type = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].strip())


def run_generation(topic: str):
    """
    Streams POST /generate and updates the UI live as progress events arrive.
    Returns the final run_id if generation completed, else None.
    """
    status_box = st.status("Starting generation...", expanded=True)
    final_markdown_placeholder = st.empty()
    run_id = None
    final_markdown = None

    try:
        with requests.post(
            f"{BACKEND_URL}/generate",
            json={"topic": topic},
            stream=True,
            timeout=600,  # generation can take a while
        ) as resp:
            resp.raise_for_status()

            for event_type, data in parse_sse_stream(resp):
                if event_type == "progress":
                    node = data.get("node", "?")
                    label = data.get("label", "")
                    status_box.write(f"**{node}** — {label}")

                elif event_type == "done":
                    run_id = data.get("run_id")
                    final_markdown = data.get("final_markdown")
                    status_box.update(label="Generation complete!", state="complete")

                elif event_type == "error":
                    status_box.update(label="Generation failed", state="error")
                    st.error(data.get("message", "Unknown error during generation."))
                    return None

    except requests.RequestException as e:
        status_box.update(label="Connection failed", state="error")
        st.error(f"Couldn't reach backend: {e}")
        return None

    if final_markdown:
        final_markdown_placeholder.markdown(rewrite_image_paths(final_markdown))
    elif run_id:
        # Backend didn't send markdown inline on "done" -- fetch it from /runs/{id}
        detail = fetch_run_detail(run_id)
        if detail and detail.get("final_markdown"):
            final_markdown_placeholder.markdown(rewrite_image_paths(detail["final_markdown"]))

    return run_id


# ---------------------------------------------------------------------------
# Sidebar: past runs
# ---------------------------------------------------------------------------

st.sidebar.title("📚 Past Runs")

if "view_run_id" not in st.session_state:
    st.session_state.view_run_id = None  # None = generator view, else viewing that past run

if st.sidebar.button("＋ New Blog", type="primary", use_container_width=True):
    st.session_state.view_run_id = None
    st.rerun()

if st.sidebar.button("🔄 Refresh list"):
    st.rerun()

runs = fetch_recent_runs()

if runs:
    for run in runs:
        label = f"#{run.get('id')} — {run.get('topic', 'untitled')}"
        if st.sidebar.button(label, key=f"run_{run.get('id')}", use_container_width=True):
            st.session_state.view_run_id = run.get("id")
            st.rerun()
else:
    st.sidebar.caption("No past runs yet — generate your first blog!")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

st.title("📝 Blog Writing Agent")
st.caption("Multi-agent blog generation with research, critique, and revision — built with LangGraph.")

# If a past run is selected, show it instead of the generator
if st.session_state.view_run_id is not None:
    run_id = st.session_state.view_run_id
    st.subheader(f"Viewing past run #{run_id}")
    detail = fetch_run_detail(run_id)
    if detail:
        st.markdown(f"**Topic:** {detail.get('topic', 'N/A')}")
        st.markdown(f"**Created:** {detail.get('created_at', 'N/A')}")
        st.divider()
        st.markdown(rewrite_image_paths(detail.get("final_markdown", "*No content saved for this run.*")))

else:
    st.subheader("Generate a new blog")

    # A form lets pressing Enter in the text field submit directly --
    # a plain st.button() can't be triggered by the Enter key on its own.
    with st.form(key="generate_form"):
        topic = st.text_input("Topic", placeholder="e.g. Attention Mechanisms in Transformers")
        generate_clicked = st.form_submit_button("🚀 Generate", type="primary")

    if generate_clicked:
        if topic.strip():
            run_generation(topic.strip())
        else:
            st.warning("Please enter a topic first.")