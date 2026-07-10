# GLMM Analysis — Which dimensions drive performance?

Mixed-effects logistic regression (random intercept per game). Odds ratios from cluster-robust logistic; `mixed_OR` from the Bayesian mixed model cross-checks them. Baseline config = **Llama / small / P0 / full / NAME error**. OR > 1 helps, OR < 1 hurts. Sig: \*\*\* p<.001, \*\* p<.01, \* p<.05.

## Recall  (base rate 0.146, game-SD 0.407)

| term | odds ratio | mixed OR | p | sig |
|---|---|---|---|---|
| Intercept | 0.101 | 0.099 | 0.0 | *** |
| family[T.qwen] | 2.802 | 2.851 | 0.0 | *** |
| size[T.medium] | 2.429 | 2.466 | 0.0 | *** |
| prompt[T.p0a] | 0.777 | 0.774 | 0.0 | *** |
| prompt[T.p0b] | 0.557 | 0.552 | 0.0 | *** |
| prompt[T.p0c] | 0.447 | 0.44 | 0.0 | *** |
| prompt[T.p0d] | 0.627 | 0.622 | 0.0 | *** |
| prompt[T.p1] | 0.484 | 0.478 | 0.0 | *** |
| prompt[T.p2] | 0.534 | 0.528 | 0.0 | *** |
| prompt[T.p3] | 0.766 | 0.763 | 0.0009 | *** |
| prompt[T.p4] | 0.437 | 0.431 | 0.0 | *** |
| mode[T.sent] | 1.823 | 1.842 | 0.0 | *** |
| category[T.CONTEXT] | 0.63 | 0.721 | 0.0169 | * |
| category[T.NOT_CHECKABLE] | 1.206 | 1.112 | 0.3269 |  |
| category[T.NUMBER] | 0.451 | 0.463 | 0.0 | *** |
| category[T.OTHER] | 0.274 | 0.23 | 0.0 | *** |
| category[T.WORD] | 0.339 | 0.32 | 0.0 | *** |
| sent_pos | 0.633 | 0.614 | 0.0 | *** |

## Precision  (base rate 0.379, game-SD 0.545)

| term | odds ratio | mixed OR | p | sig |
|---|---|---|---|---|
| Intercept | 1.321 | 1.368 | 0.0793 |  |
| family[T.qwen] | 1.471 | 1.445 | 0.0 | *** |
| size[T.medium] | 1.815 | 1.822 | 0.0 | *** |
| prompt[T.p0a] | 0.35 | 0.327 | 0.0 | *** |
| prompt[T.p0b] | 0.278 | 0.253 | 0.0 | *** |
| prompt[T.p0c] | 0.293 | 0.265 | 0.0 | *** |
| prompt[T.p0d] | 0.247 | 0.225 | 0.0 | *** |
| prompt[T.p1] | 0.303 | 0.274 | 0.0 | *** |
| prompt[T.p2] | 0.332 | 0.305 | 0.0 | *** |
| prompt[T.p3] | 0.357 | 0.333 | 0.0 | *** |
| prompt[T.p4] | 0.417 | 0.41 | 0.0 | *** |
| mode[T.sent] | 1.043 | 1.052 | 0.5355 |  |
| category[T.CONTEXT] | 1.029 | 0.97 | 0.8006 |  |
| category[T.NOT_CHECKABLE] | 2.226 | 2.248 | 0.0653 |  |
| category[T.NUMBER] | 0.475 | 0.47 | 0.0 | *** |
| category[T.OTHER] | 0.453 | 0.412 | 0.0 | *** |
| category[T.WORD] | 0.932 | 0.906 | 0.6122 |  |
| sent_pos | 1.182 | 1.129 | 0.0001 | *** |

## Token Recall  (base rate 0.168, game-SD 0.391)

| term | odds ratio | mixed OR | p | sig |
|---|---|---|---|---|
| Intercept | 0.187 | 0.181 | 0.0 | *** |
| family[T.qwen] | 3.254 | 3.317 | 0.0 | *** |
| size[T.medium] | 2.99 | 3.043 | 0.0 | *** |
| prompt[T.p0a] | 0.361 | 0.355 | 0.0 | *** |
| prompt[T.p0b] | 0.177 | 0.172 | 0.0 | *** |
| prompt[T.p0c] | 0.14 | 0.135 | 0.0 | *** |
| prompt[T.p0d] | 0.191 | 0.186 | 0.0 | *** |
| prompt[T.p1] | 0.173 | 0.168 | 0.0 | *** |
| prompt[T.p2] | 0.205 | 0.199 | 0.0 | *** |
| prompt[T.p3] | 0.345 | 0.339 | 0.0 | *** |
| prompt[T.p4] | 0.213 | 0.208 | 0.0 | *** |
| mode[T.sent] | 2.402 | 2.436 | 0.0 | *** |
| category[T.CONTEXT] | 0.4 | 0.445 | 0.0 | *** |
| category[T.NOT_CHECKABLE] | 0.638 | 0.626 | 0.0074 | ** |
| category[T.NUMBER] | 0.535 | 0.556 | 0.0 | *** |
| category[T.OTHER] | 0.089 | 0.082 | 0.0 | *** |
| category[T.WORD] | 0.289 | 0.267 | 0.0 | *** |
| sent_pos | 0.734 | 0.708 | 0.0 | *** |

## Token Precision  (base rate 0.159, game-SD 0.471)

| term | odds ratio | mixed OR | p | sig |
|---|---|---|---|---|
| Intercept | 0.152 | 0.142 | 0.0 | *** |
| family[T.qwen] | 1.23 | 1.212 | 0.0002 | *** |
| size[T.medium] | 1.482 | 1.509 | 0.0 | *** |
| prompt[T.p0a] | 1.811 | 1.864 | 0.0 | *** |
| prompt[T.p0b] | 2.837 | 2.861 | 0.0 | *** |
| prompt[T.p0c] | 2.999 | 3.048 | 0.0 | *** |
| prompt[T.p0d] | 2.771 | 2.8 | 0.0 | *** |
| prompt[T.p1] | 2.569 | 2.537 | 0.0 | *** |
| prompt[T.p2] | 2.503 | 2.534 | 0.0 | *** |
| prompt[T.p3] | 2.003 | 2.067 | 0.0 | *** |
| prompt[T.p4] | 2.69 | 2.831 | 0.0 | *** |
| mode[T.sent] | 0.939 | 0.928 | 0.0992 |  |
| category[T.CONTEXT] | 0.511 | 0.485 | 0.0 | *** |
| category[T.NOT_CHECKABLE] | 0.867 | 0.926 | 0.4633 |  |
| category[T.NUMBER] | 0.382 | 0.384 | 0.0 | *** |
| category[T.OTHER] | 0.442 | 0.427 | 0.0 | *** |
| category[T.WORD] | 0.565 | 0.575 | 0.0 | *** |
| sent_pos | 1.172 | 1.13 | 0.0001 | *** |

