from src.agent.graph import app

if __name__ == "__main__":
    topic = input("Enter blog topic: ")
    result = app.invoke(
        {
            "topic": topic,
            "mode": "",
            "needs_research": False,
            "queries": [],
            "evidence": [],
            "plan": None,
            "sections": [],
            "final": "",
        }
    )
    print(f"\nBlog saved. Title: {result['plan'].blog_title}")