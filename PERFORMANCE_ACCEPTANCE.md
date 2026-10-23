# Veil performance acceptance criteria

The user's supplied performance brief, sections01–08, governs this milestone.
Numerical thresholds are targets, not baseline facts. PERFORMANCE_REPORT.md
records measured values, failures and Not Measured items without substitution.

Release acceptance for this UI candidate: preserve palette endpoints/aliases,
all30 approved native palettes, custom privacy/provenance, settings, rollback,
exact-build guards and production pin. Pass focused UI regressions, source/data
validation, package smoke and disposable migration/rollback. Report known
threshold misses. Do not label full performance/native acceptance complete.

Full brief acceptance additionally requires every native and physical-display
check listed in NATIVE_PERFORMANCE_PROTOCOL.md and PERFORMANCE_REPORT.md.
An offline or fake-backend result cannot satisfy those native requirements.
