# Root-Cause Tracing Guide (Deep Call Stacks)

Use when call stack exceeds 5 layers. Prevents getting lost in deep traces.

## Method: Binary Bisection

1. **Find the boundary**: identify the deepest layer where data is still correct
2. **Bisect**: check the midpoint layer — correct or corrupted?
3. **Narrow**: repeat until you find the exact layer where data goes wrong
4. **Verify**: confirm the transformation at that layer is the root cause

## Execution Steps

### Step 1: Map the full call chain

```
Layer
0: [entry point] → input: [X]Layer 1: [function A] → transforms: [X → Y]Layer 2: [function B] → transforms: [Y → Z]...Layer N: [crash/error point] → expected: [W], actual: [bad value]

```
Use Grep / LSP goto-definition to trace each call.

### Step 2: Add observation pointsFor each layer, record:

- Input value (what it receives)
- Output value (what it passes on)
- Transformation logic (what it does)

### Step 3: Bisect

- Check Layer N/2: is the value correct here? - YES → problem is in layers N/2+1 to N - NO → problem is in layers 0 to N/2
- Repeat until single layer isolated

### Step 4: Analyze the bad layer

- Read the full function (every line, no skimming)
- Check: edge cases, nil handling, type conversions, goroutine boundaries
- Look for: implicit assumptions, missing validation, stale cache

## Common Patterns in Deep Stacks

| Pattern | Symptom | Typical Root Cause|
|---------|---------|-------------------|
|Value becomes nil | NPE at layer N | Missing nil check at layer N-K|
|Type assertion fails | panic: interface conversion | Wrong type propagated from upstream|
|Context cancelled | deadline exceeded | Parent context too short for deep chain|
|Stale data | outdated value at layer N | Cache not invalidated at layer M|
|Goroutine boundary | race / data corruption | Shared state without synchronization |
