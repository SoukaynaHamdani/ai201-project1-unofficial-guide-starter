"""
Milestone 6: run the 5 evaluation questions from planning.md end-to-end and
print a report you can paste into README.md.

For each question it shows: the retrieved sources + distances (retrieval quality)
and the grounded answer (if GROQ_API_KEY is set). Retrieval runs without a key.

Run:  python src/evaluate.py
"""

import os

from query import ask, retrieve

# The 5 questions from planning.md (with expected answers for your judgment column).
# NOTE: Q3 and Q4 target the mock dining CSVs, which are currently DISABLED — so
# they are expected to be out-of-scope. That is an honest, pipeline-tied failure
# case (the data was never ingested), which Milestone 6 specifically asks for.
QUESTIONS = [
    ("What payment methods are red flags for a rental/sublet scam?",
     "Untraceable methods: wire transfer, gift cards, crypto, Zelle/Venmo."),
    ("Why is a landlord being out of the country treated as a warning sign?",
     "It's the classic scam excuse to avoid showing the unit and collect a deposit first."),
    ("What do students say about lunch-rush wait times at Crossroads dining hall?",
     "Long lines ~noon, ~20 min waits. (Mock CSV — currently disabled.)"),
    ("What's an affordable late-night food option near campus on Durant?",
     "La Burrita / Steve's Korean BBQ. (Mock CSV — currently disabled.)"),
    ("Beyond paying rent, what obligation do BSC co-op members have?",
     "Workshift/chore hours and conduct-code compliance."),
]


def main():
    has_key = bool(os.environ.get("GROQ_API_KEY")) and os.environ["GROQ_API_KEY"] != "your_key_here"
    print(f"GROQ key present: {has_key} (generation {'ON' if has_key else 'OFF — retrieval only'})\n")

    for i, (q, expected) in enumerate(QUESTIONS, 1):
        print("=" * 80)
        print(f"Q{i}: {q}")
        print(f"Expected: {expected}")
        print("-" * 80)
        print("Retrieved chunks (distance | source):")
        for r in retrieve(q, k=4):
            preview = r["text"][:110].replace("\n", " ")
            print(f"  {r['distance']:.3f} | {r['metadata']['source_name']:<28} | {preview}...")
        if has_key:
            result = ask(q, k=4)
            print("\nAnswer:")
            print("  " + result["answer"].replace("\n", "\n  "))
            print("Sources: " + (", ".join(result["sources"]) or "(none — declined)"))
        print()


if __name__ == "__main__":
    main()
