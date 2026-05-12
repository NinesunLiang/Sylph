# Execution Mode Reference (lx-task-spec)

## stepwise (default)

Execute step by step, waiting for confirmation after each step.

- Best for: Complex tasks, high-risk changes, need for incremental verification
- Characteristics: Each step has Gate checking, user can adjust at any time

## race

Execute independent sub-tasks in parallel after planning.

- Best for: Multi-file independent modifications, batch refactoring, sub-tasks with no strong dependencies
- Characteristics: Fast but harder to debug

## When to Switch

During execution, simply say "use race mode" or "this is p0" and the mode adjusts without re-running the setup flow.
