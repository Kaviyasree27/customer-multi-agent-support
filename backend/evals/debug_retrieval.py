from agents.knowledge_base import retrieve_relevant_faqs
from models.feedback_model import list_faqs

TESTS = [
    "how do i get my money back for a return",
    "item came broken, can i swap it",
    "how long does shipping take",
    "is there a guarantee on electronics",
]


def main():
    print("\nFAQs in database:")
    for f in list_faqs():
        print(" -", f.get("question"))

    for q in TESTS:
        print("\nQ:", q)
        for label, dense in (("sparse", False), ("hybrid", True)):
            res = retrieve_relevant_faqs(q, top_k=3, use_dense=dense)
            shown = [(r["question"], r["score"], r["dense_score"]) for r in res]
            print(f"  {label}:", shown or "NO RESULTS")


def _run():
    try:
        from app import create_app
    except ImportError:
        return main()
    with create_app().app_context():
        main()


if __name__ == "__main__":
    _run()