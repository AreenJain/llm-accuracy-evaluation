# GLMM Analysis — Which dimensions drive performance?

Mixed-effects logistic regression (random intercept per game). Odds ratios from cluster-robust logistic; `mixed_OR` from the Bayesian mixed model cross-checks them. Baseline config = **Llama / small / P0 / full / NAME error**. OR > 1 helps, OR < 1 hurts. Sig: \*\*\* p<.001, \*\* p<.01, \* p<.05.

## Recall  (base rate 0.147, game-SD 0.404)

| term | odds ratio | mixed OR | p | sig |
|---|---|---|---|---|
| Intercept | 0.102 | 0.1 | 0.0 | *** |
| family[T.qwen] | 2.807 | 2.856 | 0.0 | *** |
| size[T.14b] | 1.199 | 1.199 | 0.024 | * |
| size[T.medium] | 2.433 | 2.469 | 0.0 | *** |
| prompt[T.p0a] | 0.777 | 0.774 | 0.0 | *** |
| prompt[T.p0b] | 0.545 | 0.54 | 0.0 | *** |
| prompt[T.p0c] | 0.414 | 0.408 | 0.0 | *** |
| prompt[T.p0d] | 0.678 | 0.673 | 0.0 | *** |
| prompt[T.p1] | 0.483 | 0.477 | 0.0 | *** |
| prompt[T.p2] | 0.534 | 0.528 | 0.0 | *** |
| prompt[T.p3] | 0.766 | 0.763 | 0.0009 | *** |
| prompt[T.p4] | 0.437 | 0.431 | 0.0 | *** |
| mode[T.sent] | 1.825 | 1.843 | 0.0 | *** |
| category[T.CONTEXT] | 0.599 | 0.694 | 0.0078 | ** |
| category[T.NOT_CHECKABLE] | 1.148 | 1.06 | 0.4786 |  |
| category[T.NUMBER] | 0.452 | 0.464 | 0.0 | *** |
| category[T.OTHER] | 0.251 | 0.215 | 0.0 | *** |
| category[T.WORD] | 0.327 | 0.308 | 0.0 | *** |
| sent_pos | 0.63 | 0.611 | 0.0 | *** |

## Precision  (base rate 0.378, game-SD 0.547)

| term | odds ratio | mixed OR | p | sig |
|---|---|---|---|---|
| Intercept | 1.349 | 1.402 | 0.0609 |  |
| family[T.qwen] | 1.473 | 1.449 | 0.0 | *** |
| size[T.14b] | 1.634 | 1.581 | 0.0 | *** |
| size[T.medium] | 1.823 | 1.828 | 0.0 | *** |
| prompt[T.p0a] | 0.347 | 0.324 | 0.0 | *** |
| prompt[T.p0b] | 0.278 | 0.255 | 0.0 | *** |
| prompt[T.p0c] | 0.282 | 0.255 | 0.0 | *** |
| prompt[T.p0d] | 0.25 | 0.227 | 0.0 | *** |
| prompt[T.p1] | 0.301 | 0.272 | 0.0 | *** |
| prompt[T.p2] | 0.329 | 0.303 | 0.0 | *** |
| prompt[T.p3] | 0.355 | 0.331 | 0.0 | *** |
| prompt[T.p4] | 0.416 | 0.407 | 0.0 | *** |
| mode[T.sent] | 1.044 | 1.055 | 0.5279 |  |
| category[T.CONTEXT] | 0.999 | 0.938 | 0.9951 |  |
| category[T.NOT_CHECKABLE] | 2.187 | 2.196 | 0.0767 |  |
| category[T.NUMBER] | 0.465 | 0.456 | 0.0 | *** |
| category[T.OTHER] | 0.442 | 0.402 | 0.0 | *** |
| category[T.WORD] | 0.891 | 0.862 | 0.409 |  |
| sent_pos | 1.18 | 1.13 | 0.0001 | *** |

## Token Recall  (base rate 0.167, game-SD 0.389)

| term | odds ratio | mixed OR | p | sig |
|---|---|---|---|---|
| Intercept | 0.189 | 0.182 | 0.0 | *** |
| family[T.qwen] | 3.265 | 3.328 | 0.0 | *** |
| size[T.14b] | 1.246 | 1.245 | 0.0264 | * |
| size[T.medium] | 2.999 | 3.053 | 0.0 | *** |
| prompt[T.p0a] | 0.36 | 0.354 | 0.0 | *** |
| prompt[T.p0b] | 0.17 | 0.165 | 0.0 | *** |
| prompt[T.p0c] | 0.127 | 0.123 | 0.0 | *** |
| prompt[T.p0d] | 0.211 | 0.205 | 0.0 | *** |
| prompt[T.p1] | 0.173 | 0.168 | 0.0 | *** |
| prompt[T.p2] | 0.204 | 0.199 | 0.0 | *** |
| prompt[T.p3] | 0.344 | 0.338 | 0.0 | *** |
| prompt[T.p4] | 0.212 | 0.207 | 0.0 | *** |
| mode[T.sent] | 2.407 | 2.442 | 0.0 | *** |
| category[T.CONTEXT] | 0.386 | 0.436 | 0.0 | *** |
| category[T.NOT_CHECKABLE] | 0.608 | 0.596 | 0.0034 | ** |
| category[T.NUMBER] | 0.534 | 0.555 | 0.0 | *** |
| category[T.OTHER] | 0.083 | 0.079 | 0.0 | *** |
| category[T.WORD] | 0.279 | 0.257 | 0.0 | *** |
| sent_pos | 0.729 | 0.704 | 0.0 | *** |

## Token Precision  (base rate 0.163, game-SD 0.477)

| term | odds ratio | mixed OR | p | sig |
|---|---|---|---|---|
| Intercept | 0.154 | 0.143 | 0.0 | *** |
| family[T.qwen] | 1.232 | 1.215 | 0.0001 | *** |
| size[T.14b] | 1.556 | 1.594 | 0.0 | *** |
| size[T.medium] | 1.485 | 1.512 | 0.0 | *** |
| prompt[T.p0a] | 1.809 | 1.868 | 0.0 | *** |
| prompt[T.p0b] | 2.834 | 2.871 | 0.0 | *** |
| prompt[T.p0c] | 2.939 | 2.997 | 0.0 | *** |
| prompt[T.p0d] | 2.811 | 2.84 | 0.0 | *** |
| prompt[T.p1] | 2.564 | 2.537 | 0.0 | *** |
| prompt[T.p2] | 2.498 | 2.534 | 0.0 | *** |
| prompt[T.p3] | 2.001 | 2.069 | 0.0 | *** |
| prompt[T.p4] | 2.685 | 2.827 | 0.0 | *** |
| mode[T.sent] | 0.938 | 0.928 | 0.0988 |  |
| category[T.CONTEXT] | 0.502 | 0.475 | 0.0 | *** |
| category[T.NOT_CHECKABLE] | 0.824 | 0.881 | 0.3416 |  |
| category[T.NUMBER] | 0.374 | 0.374 | 0.0 | *** |
| category[T.OTHER] | 0.435 | 0.42 | 0.0 | *** |
| category[T.WORD] | 0.551 | 0.561 | 0.0 | *** |
| sent_pos | 1.175 | 1.135 | 0.0001 | *** |

