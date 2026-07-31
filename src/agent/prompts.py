# planner prompt
PLANNER_SYSTEM_PROMPT = (
    "Create a blog plan with 5-7 sections on the following topic."
)

# writer prompt
WRITER_SYSTEM_PROMPT = "Write one clean Markdown section."

def build_writer_user_prompt(blog_title: str, topic: str, task) -> str:
    return (
        f"Blog: {blog_title}\n"
        f"Topic: {topic}\n\n"
        f"Section: {task.title}\n"
        f"Brief: {task.brief}\n\n"
        "Return only the section content in Markdown."
    )