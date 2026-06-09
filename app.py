"""
Milestone 5: Gradio query interface for the Unofficial Berkeley Housing Guide.

Run:  python app.py   then open http://localhost:7860

Requires GROQ_API_KEY in .env and an embedded ChromaDB store (run src/embed.py first).
"""

import os
import sys

import gradio as gr

# Make src/ importable when running `python app.py` from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from query import ask  # noqa: E402


def handle_query(question):
    question = (question or "").strip()
    if not question:
        return "Please enter a question.", ""
    try:
        result = ask(question)
    except SystemExit as e:        # e.g. missing API key
        return f"Configuration error: {e}", ""
    sources = "\n".join(f"• {s}" for s in result["sources"]) or "(no sources — out of scope)"
    return result["answer"], sources


with gr.Blocks(title="Unofficial Berkeley Housing Guide") as demo:
    gr.Markdown(
        "# 🐻 Unofficial UC Berkeley Housing & Survival Guide\n"
        "Ask about rental scams, tenant rights, co-op (BSC) rules, and campus safety. "
        "Answers are grounded only in the ingested documents and cite their sources."
    )
    inp = gr.Textbox(label="Your question", placeholder="e.g. What are red flags of a rental scam?")
    btn = gr.Button("Ask", variant="primary")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])

    gr.Examples(
        examples=[
            "What payment methods are red flags for a rental scam?",
            "Why is a landlord being out of the country a warning sign?",
            "What obligations do BSC co-op members have beyond paying rent?",
            "How much can a landlord charge for a security deposit in California?",
            "What do students say about the best dining hall?",  # out-of-scope demo
        ],
        inputs=inp,
    )


if __name__ == "__main__":
    demo.launch()
