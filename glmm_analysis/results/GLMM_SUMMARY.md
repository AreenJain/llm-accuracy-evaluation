# GLMM Analysis — Which dimensions drive performance?

Mixed-effects logistic regression (random intercept per game). Odds ratios from cluster-robust logistic; `mixed_OR` from the Bayesian mixed model cross-checks them. Baseline config = **Llama / small / P0 / full / NAME error**. OR > 1 helps, OR < 1 hurts. Sig: \*\*\* p<.001, \*\* p<.01, \* p<.05.

## Recall  (base rate 0.144, game-SD 0.395)

| term | odds ratio | mixed OR | p | sig |
|---|---|---|---|---|
| Intercept | 0.096 | 0.094 | 0.0 | *** |
| family[T.qwen] | 2.711 | 2.755 | 0.0 | *** |
| size[T.medium] | 2.708 | 2.751 | 0.0 | *** |
| prompt[T.p0a] | 0.777 | 0.773 | 0.0 | *** |
| prompt[T.p1] | 0.484 | 0.478 | 0.0 | *** |
| prompt[T.p2] | 0.534 | 0.528 | 0.0 | *** |
| prompt[T.p3] | 0.767 | 0.763 | 0.0009 | *** |
| prompt[T.p4] | 0.437 | 0.431 | 0.0 | *** |
| mode[T.sent] | 1.823 | 1.841 | 0.0 | *** |
| category[T.CONTEXT] | 0.685 | 0.767 | 0.0325 | * |
| category[T.NOT_CHECKABLE] | 1.107 | 1.01 | 0.5872 |  |
| category[T.NUMBER] | 0.437 | 0.449 | 0.0 | *** |
| category[T.OTHER] | 0.195 | 0.171 | 0.0 | *** |
| category[T.WORD] | 0.384 | 0.368 | 0.0 | *** |
| sent_pos | 0.645 | 0.63 | 0.0 | *** |

## Precision  (base rate 0.407, game-SD 0.550)

| term | odds ratio | mixed OR | p | sig |
|---|---|---|---|---|
| Intercept | 1.15 | 1.186 | 0.38 |  |
| family[T.qwen] | 1.413 | 1.39 | 0.0 | *** |
| size[T.medium] | 1.952 | 1.969 | 0.0 | *** |
| prompt[T.p0a] | 0.365 | 0.338 | 0.0 | *** |
| prompt[T.p1] | 0.308 | 0.276 | 0.0 | *** |
| prompt[T.p2] | 0.338 | 0.31 | 0.0 | *** |
| prompt[T.p3] | 0.362 | 0.334 | 0.0 | *** |
| prompt[T.p4] | 0.408 | 0.401 | 0.0 | *** |
| mode[T.sent] | 1.038 | 1.045 | 0.5743 |  |
| category[T.CONTEXT] | 1.299 | 1.265 | 0.0312 | * |
| category[T.NOT_CHECKABLE] | 2.562 | 2.561 | 0.0751 |  |
| category[T.NUMBER] | 0.54 | 0.537 | 0.0 | *** |
| category[T.OTHER] | 0.495 | 0.45 | 0.0 | *** |
| category[T.WORD] | 1.18 | 1.171 | 0.2234 |  |
| sent_pos | 1.192 | 1.136 | 0.0001 | *** |

## Token Recall  (base rate 0.176, game-SD 0.375)

| term | odds ratio | mixed OR | p | sig |
|---|---|---|---|---|
| Intercept | 0.172 | 0.167 | 0.0 | *** |
| family[T.qwen] | 3.117 | 3.175 | 0.0 | *** |
| size[T.medium] | 3.413 | 3.481 | 0.0 | *** |
| prompt[T.p0a] | 0.361 | 0.355 | 0.0 | *** |
| prompt[T.p1] | 0.173 | 0.168 | 0.0 | *** |
| prompt[T.p2] | 0.205 | 0.2 | 0.0 | *** |
| prompt[T.p3] | 0.345 | 0.339 | 0.0 | *** |
| prompt[T.p4] | 0.213 | 0.208 | 0.0 | *** |
| mode[T.sent] | 2.4 | 2.436 | 0.0 | *** |
| category[T.CONTEXT] | 0.426 | 0.464 | 0.0 | *** |
| category[T.NOT_CHECKABLE] | 0.65 | 0.616 | 0.0066 | ** |
| category[T.NUMBER] | 0.532 | 0.554 | 0.0 | *** |
| category[T.OTHER] | 0.078 | 0.076 | 0.0 | *** |
| category[T.WORD] | 0.323 | 0.301 | 0.0 | *** |
| sent_pos | 0.76 | 0.736 | 0.0 | *** |

## Token Precision  (base rate 0.149, game-SD 0.454)

| term | odds ratio | mixed OR | p | sig |
|---|---|---|---|---|
| Intercept | 0.153 | 0.142 | 0.0 | *** |
| family[T.qwen] | 1.17 | 1.158 | 0.0032 | ** |
| size[T.medium] | 1.481 | 1.513 | 0.0 | *** |
| prompt[T.p0a] | 1.803 | 1.861 | 0.0 | *** |
| prompt[T.p1] | 2.527 | 2.5 | 0.0 | *** |
| prompt[T.p2] | 2.473 | 2.512 | 0.0 | *** |
| prompt[T.p3] | 1.978 | 2.043 | 0.0 | *** |
| prompt[T.p4] | 2.65 | 2.793 | 0.0 | *** |
| mode[T.sent] | 0.937 | 0.924 | 0.082 |  |
| category[T.CONTEXT] | 0.538 | 0.514 | 0.0 | *** |
| category[T.NOT_CHECKABLE] | 0.91 | 0.964 | 0.6344 |  |
| category[T.NUMBER] | 0.415 | 0.415 | 0.0 | *** |
| category[T.OTHER] | 0.447 | 0.431 | 0.0 | *** |
| category[T.WORD] | 0.584 | 0.598 | 0.0 | *** |
| sent_pos | 1.169 | 1.128 | 0.0001 | *** |

