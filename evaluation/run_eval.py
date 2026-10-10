"""Offline evaluation: runs the agent on test cases and scores each output.

Usage (from the project root, with GROQ_API_KEY set):
    python -m evaluation.run_eval [--user-id 1] [--out evaluation/results.csv]

Cases with "use_rag": true retrieve from the knowledge base of --user-id and are additionally judged on
faithfulness, answer relevancy, context precision and completeness (LLM-as-judge approximation of RAGAS metrics).
"""
import argparse
import csv
import json
from pathlib import Path

from app.deps import get_agent
from app.services.llm_service import parse_json
from app.services.prompt_manager import render


def judge_rag(agent, topic: str, context: str, content: str) -> dict:
    prompt = render("judge", topic=topic, context=context, content=content)
    res = agent.llm.chat("You are a strict evaluation judge. Respond only with JSON.", prompt,
                         model=agent.llm.model, temperature=0.0, json_mode=True, max_tokens=300)
    data = parse_json(res.text)
    return {k: float(data.get(k, 0.0)) for k in ("faithfulness", "answer_relevancy", "context_precision", "completeness")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-id", type=int, default=1)
    ap.add_argument("--cases", default="evaluation/test_cases.json")
    ap.add_argument("--out", default="evaluation/results.csv")
    args = ap.parse_args()

    agent = get_agent()
    rows = []
    for case in json.loads(Path(args.cases).read_text(encoding="utf-8")):
        state = agent.run(args.user_id, case)
        row = {"topic": case["topic"], "type": case["content_type"], "words": len(state["draft"].split()),
               "revisions": state.get("revision_count", 0), "overall": state["review"]["overall"],
               **state["review"]["scores"],
               "flesch": state["review"]["seo_stats"]["flesch_reading_ease"],
               "tokens": state["usage"]["input_tokens"] + state["usage"]["output_tokens"],
               "latency_s": round(state["usage"]["latency"], 2)}
        if case.get("use_rag") and state.get("context"):
            row.update(judge_rag(agent, case["topic"], state["context"], state["draft"]))
        rows.append(row)
        print(f"{case['topic'][:45]:45} overall={row['overall']} tokens={row['tokens']}")

    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
