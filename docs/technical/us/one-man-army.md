# Carror OS Core Architecture Deep Dive: One-Man Army (OMA)

> **Version**: v6.1.8 (first introduced in v6.1.5)
> **Core Philosophy**: Use text files (Markdown) to carry system state; use filesystem locks (File Mutex) to coordinate AI concurrency.
> **Implementation Status**: Core lock primitives implemented (`oma_lock_manager.py`), but production-grade lifecycle enhancements pending. Known issues: `posttool-write-lock.sh` embedded newline bug causes `release_lock()` to never be called → orphan locks; TOCTOU race condition in `acquire_lock()`; 60s timeout too short for complex tasks. These issues will be fixed uniformly in RPE-014.

"One-Man Army (OMA)" is a **decentralized architecture** designed by Carror OS to coordinate multi-terminal AI concurrency. Through the `/lx-oma` instruction, it decomposes large requirements (Master PRD) into isolated sub-module directories (`rpe/feat-X/`), allowing developers to simultaneously open multiple terminals and run their respective `/lx-rpe` pipelines concurrently.

Below are the core architecture Q\&A about concurrency conflicts and state management:

---

## Q1: Do truly 100% orthogonal features exist? If two features concurrently modify the same base function and cause a logic bug, how is it prevented?

**Conclusion: In a real-world business codebase, perfect orthogonality (MECE) does not exist. Two features concurrently modifying the same base file (e.g., `utils.go` or `user_model.ts`) is an inevitability.**

Carror OS's microkernel concurrent lock (`oma_lock_manager.py`) **only solves "physical write conflicts"** (preventing two processes from simultaneously writing bytes to the same file causing corruption), but it cannot solve "semantic logic conflicts" (e.g., Feature A deletes a field while Feature B still tries to call it).

To address this, Carror OS has designed a **four-layer Defense in Depth** to prevent collisions:

### Defense Layer 1: Topological Split in Decomposition

In `/lx-oma`'s brain design, it not only slices horizontally (API / UI / DB), but also forces AI to extract a **`feat-00-core` (core foundation)**. The decomposition report explicitly prompts the developer: "**Please run `/lx-rpe feat-00-core` first** to complete the database table structures and common utilities. After completion, then **concurrently** run `feat-auth`, `feat-payment`." Through temporal dependency, this physically isolates 80% of the most dangerous underlying modification conflicts.

### Defense Layer 2: Natural Immunity of Edit Tools (Stale Context Rejection)

What if Feature B waits 3 minutes to acquire the physical lock on `main.go`, but `main.go` has already been drastically changed by Feature A? **The large model's `Edit/Replace` tool is naturally foolproof.** It must match specific code snippet context (`oldString`) before making modifications. If Feature A changed this code, when Feature B acquires the lock and attempts the replacement, the underlying system will directly throw an error: `Error: target string not found`. Upon receiving the error, the large model is **forced to re-`Read` this file**, thereby refreshing its mental context! This is a "blessing in disguise."

### Defense Layer 3: Build and Test Gates (Build-Validator Gate)

Even if both modifications succeed, but there is a logical incompatibility bug (e.g., missing interface fields). At this point, Carror OS's `build-validator` and `completion-gate` will step in. As long as `go build` or `npm test` fails, the large model **cannot mark itself as DONE**. It is stuck at the current Step, forced to fix the compilation errors.

### Defense Layer 4: A→B→A Cross-Verification

Before `git commit`, the `subagent_reviewer` launches a validator (Sub-agent) with a completely fresh context. It examines the full diff of code from both features combined from a global perspective. Any unclosed logic caused by concurrency will be ruthlessly sent back for rework.

---

## Q2: Does the One-Man Army architecture align with Carror OS's core philosophy? Does it truly achieve "Document as State Machine"?

**Conclusion: This aligns with Carror OS's "Guard First, Arm Later" and "The Less, The More" philosophy.**

It embodies the **"Document as State Machine"** design:

### 1. Decoupling and Decentralization

In traditional Multi-Agent frameworks (e.g., AutoGen, CrewAI), a centralized Python Manager process must run in the background, monitoring the state of all agents. If the main process crashes or OOMs, all agents are lost. **But in the One-Man Army (OMA) architecture, there is no central brain!** `/lx-oma` is just a relentless scaffold worker. After generating `rpe/feat-1/executor.md`, `rpe/feat-2/executor.md`, it clocks out and goes home. All terminals operate independently without interference.

### 2. True "Document as State Machine"

You open 5 terminals, running `/lx-rpe feat-1` through `feat-5` respectively. Each AI only watches its own `executor.md` (progress sheet) and `.omc/state/todo-queue.md`. What if a terminal suddenly loses power or is physically terminated by the 80% Context-Guard? **No progress is lost.** You simply open a new terminal, type `/lx-rpe feat-3` again. The large model re-reads `rpe/feat-3/executor.md`, finds "yesterday I was stuck on Step 3 Debug," and continues. The document **is** the state itself.

### 3. Primitive Mutex Aligned with UNIX Philosophy

Faced with complex concurrent modifications, we did not install heavyweight Redis or write complex RPC communication services for concurrency synchronization. We simply used a ~300-line `.claude/scripts/oma_lock_manager.py`, leveraging the operating system kernel's atomic operations (`os.O_CREAT | os.O_EXCL`). It acts like a simple mechanical lock — no matter how many large model terminals contend for a file, it simply suspends them and releases them one at a time.

**Use text files (Markdown) to carry system state; use filesystem locks (File Mutex) to coordinate AI concurrency.**
