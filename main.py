from src.agent.graph import app
from src.agent.db import init_schema

if __name__ == "__main__":
    init_schema()  # safe to call every run — creates tables only if missing

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
            "critiques": [],
            "unverified_citations": [],
            "revision_count": 0,
            "merged_md": "",
            "md_with_placeholders": "",
            "image_specs": [],
            "final": "",
            "run_id": None,
        },
        config={"max_concurrency": 2},
    )

    print(f"\nBlog saved. Title: {result['plan'].blog_title}")
    print(f"Run ID: {result.get('run_id')}")

    print("\n=== CRITIC REPORT ===")
    print(f"Revision passes used: {result.get('revision_count', 0)}")
    for c in result.get("critiques", []):
        status = "✅ PASS" if c["passes"] else "❌ FAIL"
        print(f"  Section {c['task_id']}: {status}")
        for issue in c.get("issues", []):
            print(f"    - {issue}")

    unverified = result.get("unverified_citations", [])
    if unverified:
        print(f"\n⚠️  {len(unverified)} unverified citation(s):")
        for url in unverified:
            print(f"   - {url}")
    else:
        print("\n✅ All citations verified against evidence.")