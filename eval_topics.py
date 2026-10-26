"""
Eval topic set for AutoBlog. Spans all three router modes so the eval
reflects real usage, not just one code path:
  - closed_book: evergreen concepts, no research needed
  - hybrid: evergreen but benefits from current examples/tools
  - open_book: volatile, "latest"/"this week" style topics
"""

EVAL_TOPICS = [
    # --- closed_book (evergreen fundamentals) ---
    "Attention Mechanism in Transformers",
    "The Encoder-Decoder Architecture of Transformer",
    "Backpropagation Explained for Deep Learning Engineers",
    "Overfitting and Regularization Techniques in Machine Learning",
    "Convolutional Neural Networks for Image Classification",
    "Gradient Descent Variants: SGD, Momentum, Adam",
    "Understanding Word Embeddings and Word2Vec",
    "Recurrent Neural Networks and the Vanishing Gradient Problem",
    "Batch Normalization and Why It Works",
    "The Bias-Variance Tradeoff in Machine Learning",

    # --- hybrid (evergreen concept + current tools/examples) ---
    "Retrieval-Augmented Generation (RAG) Systems",
    "Fine-Tuning Large Language Models with LoRA",
    "Vector Databases for Semantic Search",
    "Prompt Engineering Best Practices for Production LLM Apps",
    "Building Multi-Agent Systems with LangGraph",
    "Model Context Protocol (MCP) for AI Agents",
    "Quantization Techniques for Deploying LLMs Efficiently",
    "Evaluating LLM Outputs: Metrics and Frameworks",
    "Serving LLMs at Scale: vLLM and Inference Optimization",
    "Building AI Agents with Tool Use and Function Calling",

    # --- open_book (volatile, needs research) ---
    "Latest Developments in Open-Source LLMs This Month",
    "Recent AI Regulation News and Policy Changes",
    "This Week's Major AI Model Releases",
    "Latest Pricing Changes Among Major LLM API Providers",
    "Recent Breakthroughs in AI Agent Benchmarks",
    "Latest News on AI Chip Manufacturing and Nvidia Competitors",
    "This Month's Notable AI Startup Funding Rounds",
    "Recent Controversies in AI Safety and Alignment",
    "Latest Updates to Popular AI Coding Assistants",
    "This Week's Developments in Multimodal AI Models",
]