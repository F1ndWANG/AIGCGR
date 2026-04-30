from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.evaluation import evaluate_recommendation  # noqa: E402
from app.models import RecommendationRequest, RecommendationResponse  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a LifeRec recommendation response.")
    parser.add_argument("--request", required=True, help="Path to RecommendationRequest JSON.")
    parser.add_argument("--response", required=True, help="Path to RecommendationResponse JSON.")
    args = parser.parse_args()

    request = RecommendationRequest.model_validate_json(Path(args.request).read_text(encoding="utf-8"))
    response = RecommendationResponse.model_validate_json(Path(args.response).read_text(encoding="utf-8"))
    report = evaluate_recommendation(request, response)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
