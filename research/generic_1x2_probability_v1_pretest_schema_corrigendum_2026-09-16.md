# PBK Generic 1X2 Probability V1 — pre-TEST schema corrigendum

This correction was discovered after the pre-TEST gate returned `TEST_ALLOWED`, but before any TEST outcomes were read.

The canonical `Football_Top5_2016-2026.csv` snapshot has always used the lowercase column name `season`. PR #59 incorrectly encoded the name as `Season` in the evaluator configuration and row lookup.

This is an execution/schema-only correction. It changes neither the model nor the locked TRAIN/TEST split, features, optimizer, thresholds, leagues, classes, calibration rule, or gate criteria. The evaluator now reads the exact canonical schema name.

TEST remained unopened while this corrigendum was prepared. No canonical TEST result, metric, or outcome informed this correction.

