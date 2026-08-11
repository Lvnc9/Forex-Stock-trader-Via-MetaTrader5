# Handoff — Agent 2 (Labels & Fixtures)

Build / validate a label + fixture set that matches `hs-spec.v1.json` → `label_schema_expected`.

## Required fields per labeled H&S
`symbol`, `timeframe`, `direction` (`top`|`inverse`),  
`LS_time`, `LS_price`, `left_armpit_time`, `left_armpit_price`,  
`head_time`, `head_price`, `right_armpit_time`, `right_armpit_price`,  
`RS_time`, `RS_price`,  
`confirm_time`, `confirm_price`, `confirm_rule` (`close_beyond_neckline`|`close_beyond_right_armpit`),  
`H`, `label_quality` (`gold`|`silver`|`reject`)

## Optional but needed for entry/TP metrics
`entry_mode` (`A`|`B`), `entry_time`, `entry_price`, `sl_price`,  
`tp1_price`, `tp2_price`, `tp1_hit`, `tp2_hit`, `false_positive`, `notes`

## Agent 2 outcomes
1. Schema-valid JSON/CSV labels (no copyrighted chart dumps — our pivots only).
2. At least one fixture per confirmation branch (top/inverse × neckline up/down/flat).
3. Reject-class rows for hard fails (sequence, prominence, prior trend, slope).
4. Do not implement EA logic; do not edit detector code unless asked.
