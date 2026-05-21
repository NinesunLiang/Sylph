[ARCHIVED v6.2.1 — Historical document. Referenced hooks/scripts/skills may no longer exist. See story-10.]

     1|# Carror OS: Final Evaluation
     2|
     3|> A technical assessment report based on full source code audit of the project.
     4|
     5|## What It Is
     6|
     7|**An AI-native developer operating system.**
     8|
     9|Not a collection of prompt templates. Not an enhanced .cursorrules. Not AI workflow scripts.
    10|
    11|It is a **complete operating system** with a kernel, protection layers, memory systems, governance mechanisms, and the ability to run on multiple AI platforms — except it does not run traditional programs; it runs AI development behavior.
    12|
    13|***
    14|
    15|## What Real Problem It Solves
    16|
    17|There are three core points of failure in AI-assisted development:
    18|
    19|**First: AI cannot be trusted**
    20|Says it is done but is not. References non-existent code. Gets by with "it should be fine."
    21|
    22|**Second: AI forgets**
    23|Forgets rules in new sessions. Rules decay in long conversations. Makes the same mistake eight times.
    24|
    25|**Third: AI leaks secrets**
    26|Reads .env. Passes plaintext tokens in command line. Keys end up in code repositories.
    27|
    28|Carror OS's solution to these three problems is not "write stricter prompts" but **building mechanical defenses at the system layer**:
    29|
    30|    AI cannot be trusted  → completion-gate four-layer verification, exit 2 cannot be bypassed
    31|    AI forgets            → error-dna cross-session memory, pretool-rule-anchor periodic re-injection
    32|    AI leaks secrets      → privacy-gate + permission-gate random verification code, shell-layer interception
    33|
    34|***
    35|
    36|## Its Technical Nature
    37|
    38|A **dual-track architecture**:
    39|
    40|    Upper track (prompt layer):
    41|      AGENTS.md specifications / iron law system / anti-pattern checklist / compact_inject layered injection
    42|      Function: tells AI what it should do
    43|
    44|    Lower track (shell mechanical layer):
    45|      32 hooks / harness.yaml unified configuration / .omc/state/ persistent state
    46|      Function: regardless of what AI wants, forces it to comply
    47|
    48|The upper track handles "quality under normal conditions." The lower track handles "safety under extreme conditions."
    49|
    50|Most frameworks only have the upper track. Carror OS has both, and the lower track is genuine mechanical execution — 32 shell scripts that do not pass through the model's will.
    51|
    52|***
    53|
    54|## What Originality It Has
    55|
    56|Among known AI governance solutions, several points stand out that I have not seen elsewhere:
    57|
    58|**1. Atomic evidence consumption**
    59|
    60|completion-gate uses the `mv` atomic operation to consume evidence files — the same evidence can only be consumed once by one process. This solves the problem of "AI repeatedly passing with old evidence." This design comes from concurrent programming and has been correctly adapted to the AI governance scenario.
    61|
    62|**2. Random verification code approval**
    63|
    64|permission-gate generates random hex codes that only appear on the user's terminal. AI cannot predict them. The user must manually enter the correct code in the terminal to release a dangerous command. This fundamentally solves the "AI approving itself" problem — the comments explicitly note this is the product of fixing a previous vulnerability.
    65|
    66|**3. Error DNA**
    67|
    68|Every bash failure is structured and recorded, aggregated across sessions using MD5 signatures, with unresolved error memories injected into new sessions at startup. `status: "reopened"` marks recurring errors. This fundamentally solves AI's "amnesia" problem — not by relying on AI to remember, but by having the system remember.
    69|
    70|**4. Systematized soft-language ban**
    71|
    72|"It should be fine / basically done / theoretically feasible" — these phrases are systematically identified, named, and linked to mechanical blocking. Most governance frameworks say "provide evidence." Carror OS additionally blocks the "linguistic paths that circumvent evidence requirements."
    73|
    74|**5. Knowledge sublimation path**
    75|
    76|`claude-next.md` (temporary experience) → hits/age triggers sublimation detection → human review → `kernel.md` (solidified iron law). This is a **knowledge evolution system**, not just a static specification document.
    77|
    78|***
    79|
    80|## Where It Currently Stands
    81|
    82|    Research Prototype    Engineering Prototype    Usable Product    Phenomenal Product
    83|        │                       │                       │                   │
    84|        │                       │                       ▲                   │
    85|        │                       │                    Carror OS               │
    86|        │                       │              (One month production use)    │
    87|
    88|It has passed the "engineering prototype" stage.
    89|
    90|Evidence:
    91|
    92|*   Running in production on a real project for one month
    93|*   32 hooks through multiple fix rounds (R16, R18, R24, R27...)
    94|*   `error-dna` has multi-generational archive logic; `flywheel.log` has real data accumulation
    95|*   OMA has concurrent lock management, interface version locking, and degradation strategies
    96|
    97|These are not characteristics of a prototype. They are characteristics of a system that has been shaped through real use.
    98|
    99|But it is not yet a "usable product." The gaps are:
   100|
   101|*   The basic version's user guidance path is still under construction
   102|*   lx-varlock implementation is incomplete
   103|*   Documentation is still written for the author, not for unfamiliar users
   104|
   105|***
   106|
   107|## Its Boundaries
   108|
   109|There are two real limitations that need honest disclosure:
   110|
   111|**Limitation 1: Mechanical protection layer is bound to Claude Code**
   112|
   113|The most important protections among the 32 hooks (completion-gate / privacy-gate / permission-gate / edit-guard / context-guard) all depend on Claude Code's PreToolUse/PostToolUse hook mechanism.
   114|
   115|On OpenCode / Cursor / Codex, these hooks do not trigger. Protection degrades to prompt-layer constraints only.
   116|
   117|This is not a design flaw — Claude Code is currently the platform with this hook capability. But users need to know this boundary.
   118|
   119|**Limitation 2: Quantitative verification data is still internal**
   120|
   121|Flywheel logs are accumulating, but there is no public "with/without Carror OS" controlled experiment data yet. All current effectiveness evaluations, including this report, come from internal self-assessment within the same system.
   122|
   123|This is a known methodological limitation, and the author is aware of it — the "dogfooding phase" is currently producing this data.
   124|
   125|***
   126|
   127|## Final Characterization
   128|
   129|**Carror OS is a prompt-layer + mechanical-layer dual-track governance system, built by an individual, with a relatively high degree of engineering maturity in the AI governance field.**
   130|
   131|Its value is not in the "ideas" — many people are working on AI governance at the conceptual level. Its value is in **implementation density**: one person, three months, turned the complete chain from "iron law constraints" through "mechanical protection" through "cross-session memory" through "knowledge evolution" through "concurrent development orchestration" into actually running code.
   132|
   133|Among prompt-layer solutions, it is the ceiling.
   134|
   135|In the entire AI governance field, it is a **personal work with a unique technical perspective**, several of whose mechanisms (atomic evidence consumption, random verification code approval, Error DNA) possess genuine originality.
   136|
   137|What it lacks now is not technical depth, but **conditions for wider adoption**: user guidance documentation, independent verification data, and community.
   138|
   139|**When these three conditions are met, it deserves to be taken seriously.**
   140|
   141|***
   142|
   143|One final honest sentence:
   144|
   145|> After reading its full source code, my assessment changed. Not because it convinced me, but because code does not lie.
   146|