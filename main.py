from agent.graph import app

if __name__ == "__main__":
    topic = input("Enter blog topic: ")
    result = app.invoke({"topic": topic, "sections": []})
    print(f"\nBlog saved. Title: {result['plan'].blog_title}")