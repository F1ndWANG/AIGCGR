# Algorithm Innovation Roadmap

This document defines the algorithm-level innovation plan for LifeRec. The goal is to evolve the current MVP from a rule-based AIGC recommendation demo into an executable daily-life generative recommendation system.

Core research direction:

```text
LifeRec-Ranker
= Intent Understanding
+ Life State Vector
+ Realness Guard
+ Execution-aware Multi-objective Reranking
+ Plan Feedback Learning
```

Recommended project framing:

```text
LifeRec: A Context-Aware Generative Recommendation System for Executable Daily Life Planning
```

## 1. Current Algorithm Baseline

The current system already includes:

- Rule-based scenario detection for diet, restaurant, shopping, and travel.
- Dynamic POI, weather, and walking-route context from Amap.
- AIGC strategy summaries and AIGC product need generation.
- Runtime user memory from meals, wellness logs, preferences, feedback, plans, and recommendation history.
- Feedback-aware reranking.
- Request-level refresh with exclusion of previous recommendation items.
- Strict real-data mode to prevent local samples from pretending to be real provider results.
- Plan management with status, schedule time, JSON export, and ICS export.

The next stage should focus on turning these components into explicit algorithm modules with measurable metrics.

Current algorithm upgrade status:

- Phase 1 `RecommendationTrace`: implemented. Each recommendation now exposes ranker, score formula, data sources, evidence, penalties, and confidence.
- Phase 2 `LifeStateEncoder`: implemented. The backend now exposes a reusable Life State Vector across recommendation, user context, daily brief, and memory export APIs.
- Phase 3 `ExecutionCostScorer`: implemented. Recommendations now expose executable score, execution cost, blockers, evidence, and execution-aware reranking.

## 2. Highest-Value Innovation Themes

### 2.1 Life State Vector

Convert user context into a structured state representation.

Signals:

- Recent meal tags.
- Wellness tags, sleep, exercise, stress, and mood.
- Location, radius, weather, route availability, and city.
- Budget, taste, avoid tags, allergies, health goals, and travel style.
- Active plans and scheduled execution time.
- Recommendation history and feedback history.

Why it matters:

- It becomes the central algorithm object for ranking, AIGC prompting, daily briefs, and evaluation.
- It makes the system different from a generic chatbot or static recommender.

Initial implementation:

- Add `backend/app/life_state.py`.
- Define `LifeState` and `LifeStateEncoder`.
- Output normalized fields, sparse tags, confidence scores, and timestamps.
- Use the encoder in `/api/recommend`, `/api/user/daily-brief`, and evaluation scripts.

### 2.2 Executable Recommendation Score

Rank recommendations by whether the user can realistically act on them now.

Score components:

- Distance cost.
- Time cost.
- Budget fit.
- Physical effort.
- Decision complexity.
- Plan conflict.
- Weather friction.
- Data confidence.

Suggested formula:

```text
executable_score =
  0.25 * preference_score
+ 0.20 * health_score
+ 0.15 * budget_score
+ 0.15 * distance_score
+ 0.10 * context_score
+ 0.10 * execution_cost_score
+ 0.05 * realness_score
```

Initial implementation:

- Add `ExecutionCostScorer`.
- Add `execution_cost` to `ScoreBreakdown`.
- Update recommendation cards to show why something is easy or hard to execute.

### 2.3 Plan-aware Recommendation

Use active, completed, and canceled plans as ranking signals.

Rules:

- Active plans should reduce duplicate recommendations.
- Scheduled plans should avoid time conflicts.
- Done plans should increase confidence in related tags.
- Canceled plans should trigger a soft penalty for similar items unless the reason is known.

Initial implementation:

- Add `PlanAwareRanker`.
- Penalize recommendations similar to current active plans.
- Boost tags from completed plans.
- Add plan conflict metadata to recommendation cards.

### 2.4 Plan Completion Feedback Loop

Use execution outcomes as stronger feedback than simple likes.

Feedback strength:

```text
done > plan > save > like > view > skip > dislike > canceled
```

Why it matters:

- The project should optimize for real execution, not only user clicks.
- This creates a measurable difference from common recommendation demos.

Initial implementation:

- Store plan completion events as high-confidence positive feedback.
- Store canceled plans as negative or uncertain feedback.
- Add `completion_weight` into tag preference learning.

### 2.5 AIGC Hallucination Guard

Prevent LLM output from inventing provider-backed facts.

Guard rules:

- LLM cannot invent restaurants, addresses, menus, prices, routes, SKU links, inventory, or discounts.
- Provider-backed facts must include `source`, `provider`, or trace metadata.
- AIGC product output must be labeled as product need generation, not real SKU recommendation.

Initial implementation:

- Add `AIGCVerifier`.
- Check generated text and product ideas for forbidden claims.
- Add `realness_score` and `hallucination_risk` to response metadata.
- Fail or downgrade outputs in `STRICT_REAL_DATA=true`.

## 3. User State Modeling Ideas

Potential modules:

- Dynamic Life State Vector.
- Short-term context and long-term preference dual tower.
- Time-decay weighting for meals, wellness logs, feedback, and plans.
- Health constraint state machine.
- Intent uncertainty modeling.
- Multi-granularity profiles: user-level, scenario-level, location-level, time-of-day-level.
- Life rhythm modeling for breakfast, lunch, dinner, commute, weekend travel, and shopping habits.
- Context completeness scoring.

Implementation priority:

1. Time-decay weighting.
2. Context completeness score.
3. Short-term and long-term profile separation.
4. Life rhythm modeling.

## 4. Generative Recommendation Ideas

Potential modules:

- LLM-generated intent structure followed by deterministic ranking.
- LLM-generated search strategy when real POI results are missing.
- AIGC explanation for each ranked item.
- Counterfactual explanation: what would change if budget, distance, or diet constraints changed.
- AIGC plan decomposition into steps.
- AIGC self-check before returning final response.
- Multi-agent candidate generation with one shared ranker.

Safe design principle:

```text
LLM can generate reasoning, plans, and product needs.
LLM cannot generate unverifiable provider-backed facts.
```

## 5. Ranking and Reranking Ideas

Potential modules:

- Multi-objective ranker.
- Diversity reranker.
- Feedback-weight learner.
- Bandit exploration strategy.
- Context-aware scenario weights.
- Anti-fatigue recommendation.
- Negative feedback attribution.
- Realness-aware ranking.
- Weather-aware ranking.
- Route-aware ranking.

Scenario-specific weight examples:

| Scenario | Higher Weight | Lower Weight |
|---|---|---|
| Restaurant | distance, health, budget | novelty |
| Shopping | budget, usefulness, health goals | distance |
| Travel | weather, interest, time cost | immediate distance |
| Daily brief | risk flags, active plans, context completeness | novelty |

## 6. Trust and Real Data Ideas

Potential modules:

- Provider Confidence Score.
- Realness Score.
- Cache freshness score.
- Recommendation evidence chain.
- Data-source-aware ranking.
- Strict real-data gate.
- AIGC hallucination checker.

Recommended metadata for each item:

```json
{
  "realness_score": 0.92,
  "provider_confidence": 0.88,
  "cache_age_seconds": 120,
  "evidence": [
    "amap.poi",
    "user.preference",
    "runtime.meal_tags",
    "route.walking"
  ]
}
```

## 7. Feedback Learning Ideas

Signals to learn from:

- Like.
- Dislike.
- Save.
- Plan.
- Scheduled plan.
- Done plan.
- Canceled plan.
- Refresh request.
- Exported plan or memory.

Learning strategy:

- Maintain tag-level positive and negative weights.
- Apply time decay to old feedback.
- Use stronger weights for execution feedback.
- Separate scenario-level preference weights.
- Use negative feedback to penalize related tags, not only exact items.

Suggested event weights:

| Event | Weight |
|---|---:|
| done | 1.00 |
| scheduled_plan | 0.85 |
| plan | 0.75 |
| save | 0.60 |
| like | 0.50 |
| refresh | -0.20 |
| skip | -0.35 |
| dislike | -0.70 |
| canceled | -0.55 |

## 8. Evaluation Metrics

The project should add metrics that reflect executable daily-life recommendation quality.

Core metrics:

- `Executable Recommendation Score`: whether a result can be acted on now.
- `Plan Conversion Rate`: recommendation to plan.
- `Plan Completion Rate`: plan to done.
- `Health Conflict Rate`: recommendation violates recent health or wellness constraints.
- `Realness Score`: provider-backed, verifiable data ratio.
- `AIGC Hallucination Rate`: generated claims without real evidence.
- `Context Completeness Score`: quality of available user context.
- `Diversity Score`: lack of repeated item types, tags, and places.
- `Refresh Novelty Score`: replacement result does not repeat previous item or near-duplicate.
- `User Burden Score`: time, distance, budget, and decision complexity.

Initial evaluation file:

```text
scripts/evaluate_recommendations.py
```

Recommended next additions:

- Add execution cost checks.
- Add realness score checks.
- Add plan conflict checks.
- Add recommendation trace checks.
- Add hallucination guard checks.

## 9. Step-by-step Implementation Plan

### Phase 1: Make Current Ranking Explainable

Goal:

- Every recommendation should expose its scoring trace.

Status:

- Implemented in `RecommendationTrace`.
- Frontend recommendation cards can expand an algorithm trace panel.
- Tests assert trace sources, evidence, penalties, and confidence.

Tasks:

- Add `RecommendationTrace`. Done.
- Include score components, data sources, and penalties. Done.
- Show trace summary in frontend cards. Done.
- Extend tests to assert trace fields. Done.

Expected outcome:

- Users and developers can see why an item ranked high.

### Phase 2: Add Life State Vector

Goal:

- Create a reusable context encoder.

Tasks:

- Add `backend/app/life_state.py`. Done.
- Encode meals, wellness, preferences, plans, feedback, and recommendations. Done.
- Add context completeness score, confidence, normalized signal vector, and missing-data warnings. Done.
- Use the encoded state in recommender, user context, daily brief, and memory export. Done.
- Show Life State Vector in the frontend sidebar. Done.
- Add API and recommender tests for runtime-derived Life State. Done.

Expected outcome:

- Recommendation logic becomes more modular and research-friendly.

### Phase 3: Add Execution-aware Ranking

Goal:

- Rank by actionability, not just relevance.

Tasks:

- Add `ExecutionCostScorer`. Done.
- Add `execution_cost` and `executable_score`. Done.
- Penalize far, expensive, complex, route-unknown, data-risky, or weather-unfriendly options. Done.
- Blend executable score into final recommendation ranking. Done.
- Show execution score, cost, blockers, and evidence in frontend cards. Done.
- Add tests for low-burden recommendations and evaluation warnings. Done.

Expected outcome:

- Recommendations become more realistic for daily use.

### Phase 4: Add Plan-aware Ranking

Goal:

- Use plans as first-class recommendation signals.

Status:

- Implemented in `PlanAwareRanker`.
- Recommendation cards expose plan-aware score adjustments and blockers.
- Plan status updates to `done` or `canceled` are stored as feedback events.

Tasks:

- Boost tags from completed plans. Done.
- Penalize duplicates with active plans. Done.
- Penalize tags from canceled plans. Done.
- Detect schedule conflicts. Done.
- Add plan conflict metadata. Done.
- Store done/canceled plan outcomes as feedback events. Done.
- Add tests for plan-aware ranking and plan feedback events. Done.

Expected outcome:

- The system starts learning from actual user execution.

### Phase 5: Add Realness and Hallucination Guard

Goal:

- Make AIGC safe and provider-grounded.

Status:

- Implemented in `AIGCVerifier`.
- Recommendation and product items expose `realness` metadata.
- Product generation filters forbidden claims in strict real-data mode.

Tasks:

- Add `AIGCVerifier`. Done.
- Add forbidden-claim checks for links, SKU, inventory, discounts, realtime price, and real menus. Done.
- Add realness score and hallucination risk. Done.
- Add realness metadata to recommendation and product items. Done.
- Add strict-mode enforcement tests. Done.
- Show realness and hallucination risk in frontend cards. Done.

Expected outcome:

- The project can claim a clear boundary between real data and generated content.

### Phase 6: Add Feedback Weight Learning

Goal:

- Move from fixed rules to adaptive user-level ranking.

Tasks:

- Add weighted tag profile.
- Apply time decay.
- Separate positive and negative scenario-level feedback.
- Use done/canceled plans as strong feedback.

Expected outcome:

- The same query can produce different rankings for different users.

### Phase 7: Add Bandit Exploration

Goal:

- Balance known preferences and new options.

Tasks:

- Add explore/exploit ratio.
- Use UCB or Thompson Sampling for tag and item exploration.
- Track whether exploration results get positive feedback.

Expected outcome:

- The system avoids getting stuck in repetitive recommendations.

## 10. Recommended First Three Tasks

Start with these because they are high-value and fit the current codebase:

1. Add `RecommendationTrace`.
2. Add `LifeStateEncoder`.
3. Add `ExecutionCostScorer`.

These three create the foundation for nearly all later innovation.

## 11. Research Contribution Summary

Potential contribution statement:

```text
LifeRec proposes an executable generative recommendation framework for daily-life planning.
It combines real-time provider data, runtime user memory, AIGC reasoning, realness constraints,
and plan-completion feedback to optimize recommendations for actionability rather than only relevance.
```

Potential paper or open-source keywords:

- Context-aware recommendation.
- Generative recommendation.
- Executable recommendation.
- Plan-aware ranking.
- AIGC hallucination guard.
- Realness-aware recommendation.
- Daily-life planning.
- User memory feedback loop.
