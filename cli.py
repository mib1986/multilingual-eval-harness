"""Command line entry point: evalkit report / validate."""

from __future__ import annotations

import argparse
import sys

from evalkit import analyze, report, rubric


def _pct(value) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def _num(value) -> str:
    return "—" if value is None else f"{value:.3f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evalkit",
        description="Rubric-based evaluation harness: score consistency, rater bias and arbitration queue.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("report", help="compute agreement and write a Markdown report")
    run.add_argument("--rubric", required=True, help="path to rubric.json")
    run.add_argument("--annotations", required=True, help="path to annotations.jsonl")
    run.add_argument("--out", default=None, help="write the Markdown report to this path")
    run.add_argument("--spread", type=int, default=None, help="override the spread threshold")
    run.add_argument("--mad", type=float, default=None, help="override the mean-deviation threshold")
    run.add_argument("--top", type=int, default=10, help="how many arbitration rows to list")

    check = sub.add_parser("validate", help="validate a rubric file")
    check.add_argument("--rubric", required=True, help="path to rubric.json")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "validate":
        data = rubric.load_rubric(args.rubric)
        print(f"ok: {data['name']} v{data['version']}, {len(data['dimensions'])} dimensions")
        for dim in data["dimensions"]:
            print(f"  - {dim['id']} ({dim.get('label_zh', '')}) weight={dim['weight']}")
        return 0

    try:
        spec = rubric.load_rubric(args.rubric)
        records = analyze.load_annotations(args.annotations)
    except (rubric.RubricError, analyze.AnnotationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    result = analyze.compute(records, spec, spread_threshold=args.spread, mad_threshold=args.mad)
    markdown = report.to_markdown(result, source=args.annotations, top=args.top)

    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(markdown + "\n")
        print(f"report written to {args.out}")

    overall = result["overall"]
    print(
        "items={n_items} raters={n_raters} exact={exact} adjacent={adj} kappa={kappa}".format(
            n_items=result["n_items"],
            n_raters=result["n_raters"],
            exact=_pct(overall["exact_rate"]),
            adj=_pct(overall["adjacent_rate"]),
            kappa=_num(overall["kappa"]),
        )
    )
    print(f"arbitration queue: {len(result['disagreements'])}")
    if not args.out:
        print()
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
