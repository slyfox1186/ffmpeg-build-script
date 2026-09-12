# Python migration audit

This audit uses the documented CLI, configuration and supported-host contracts
as its specification. Native builds and privileged installation require separate
evidence from the fixture suite. Findings below are updated as fixes land.

## High severity: process cancellation

Build commands now run in their own process groups. On cancellation or output
failure, the runner terminates the group, escalates to kill, and waits for the
direct child before unwinding. This covers ordinary compiler descendants;
programs that deliberately detach or change credentials require their own
shutdown protocol. Debug output uses bounded chunks and file-backed stdin to
avoid pipe deadlocks. Optional desktop notifications have a deadline and cannot
mask the original error. Captured non-UTF-8 diagnostics use replacement decoding.

Real subprocess regressions check descendant writes after cancellation in quiet,
debug, terminal and capture modes, plus simultaneous large input/output.
The Python [subprocess documentation](https://docs.python.org/3/library/subprocess.html)
and Context7's CPython documentation informed process-group and pipe handling.

## Review evidence

OpenRouter's coding panel reviewed PLAN.md and repository scripts, modules,
tests, configuration and documentation. Fixtures were sent in a second batch
because the tool's combined attachment limit is 600,000 characters. No ignored
credentials or local configuration were sent. Kimi K3 and GLM 5.3 returned final
reviews after earlier responses exhausted their reasoning budgets.

Their findings are advisory: subprocess.run does kill its direct child when a
BaseException escapes, contrary to one review's claim. The demonstrated gap is
descendant processes. Review disagreements and other accepted/rejected findings
are recorded with the corresponding fixes below.
