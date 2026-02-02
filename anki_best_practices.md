# Anki and Spaced Repetition Best Practices

A research-backed guide for creating effective flashcards.

---

## The Science Behind Spaced Repetition

Spaced repetition is the **strongest evidence-based learning technique** available. The core findings:

- **Spacing Effect** (Ebbinghaus, 1885): Information is retained better when reviewed at increasing intervals rather than crammed
- **Testing Effect**: Successful recall from memory yields superior retention vs. passive re-reading
- **Delayed Testing**: Recalling after a delay is more effective than immediate recall

Research consistently shows:
- Spacing is more effective than massing for **90% of participants**
- Medical students using spaced repetition achieved **88% avg test scores** vs. **78%** for non-users
- Yet 72% of students believe cramming is more effective (it's not)

**Sources:**
- [Ebbinghaus' research and the spacing effect - Wikipedia](https://en.wikipedia.org/wiki/Spaced_repetition)
- [Kornell (2009) - Spacing Is More Effective Than Cramming](https://web.williams.edu/Psychology/Faculty/Kornell/Publications/Kornell.2009b.pdf)
- [PMC Study on Medical Education](https://pmc.ncbi.nlm.nih.gov/articles/PMC8368120/)

---

## Wozniak's 20 Rules of Formulating Knowledge

Dr. Piotr Wozniak (creator of SuperMemo, whose algorithm became Anki) published this foundational guide in 1999. These rules are the **gold standard** for flashcard creation.

### The Most Critical Rules (in priority order)

#### 1. Do Not Learn If You Do Not Understand
Master foundational comprehension before memorization. Learning without understanding produces negligible value.

#### 2. Learn Before You Memorize
Build the overall picture first. Only when pieces fit into a coherent structure can you dramatically reduce learning time.

#### 3. Build Upon the Basics
Start simple. Basics are easy to retain and prevent costly memory lapses in foundational concepts.

#### 4. Stick to the Minimum Information Principle
**The most frequently violated rule.** Formulate material as simply as possible. Simple items:
- Are easier to schedule
- Reduce cognitive load during recall
- Create more flexible knowledge

### Card Design Rules

#### 5. Cloze Deletion is Easy and Effective
Use sentences with blanks: "The {{mitochondria}} is the powerhouse of the cell."
Fast to create, strong mnemonic power.

#### 6. Use Imagery
Visual processing is stronger than verbal. One picture is worth a thousand words.

#### 7. Use Mnemonic Techniques
Mind maps, peg lists, memory palaces. With training, these dramatically accelerate memorization.

#### 8. Graphic Deletion Works Like Cloze
Mask image portions. Works especially well for anatomy, geography, diagrams.

### What to Avoid

#### 9. Avoid Sets
Don't memorize unordered collections. "Nearly impossible to memorize sets containing more than five members."

#### 10. Avoid Enumerations
Ordered lists are still difficult. Break them into overlapping cloze questions or individual cards.

#### 11. Combat Interference
Similar items confuse memory. Use specific examples, context cues, and emotional connections to distinguish competing memories.

### Optimization Rules

#### 12. Optimize Wording
Minimal, precise language. Remove redundancy that doesn't support the target knowledge.

#### 13. Refer to Other Memories
Link new items to established knowledge for better context.

#### 14. Personalize and Provide Examples
Connect to your personal life. Personal examples are "very resistant to interference."

#### 15. Rely on Emotional States
Vivid, emotionally engaging examples enhance recall.

#### 16. Use Context Cues
Label categories (e.g., "bioch:" for biochemistry). Context reduces explanation needs.

#### 17. Redundancy Does Not Contradict Minimum Information
Some repetition is beneficial. Learning word pairs both directions strengthens knowledge.

#### 18. Provide Sources
Include citations for non-obvious facts. Helps verify and update later.

#### 19. Date Stamp Volatile Knowledge
Mark time-sensitive information with dates or versions.

#### 20. Prioritize
Focus on what matters most. Use incremental reading to extract key concepts.

**Source:** [SuperMemo - Twenty Rules of Formulating Knowledge](https://www.supermemo.com/en/blog/twenty-rules-of-formulating-knowledge)

---

## Practical Guidelines for Card Creation

### The "One Thing" Rule
Cards should ask about **exactly one thing** and permit **exactly one answer**.

**Bad:** "Describe Python"
**Good:** "Who designed Python?" → "Guido von Rossum"

### Avoid Ambiguous Answers

**Bad:** "The Articles of Confederation had no power to regulate {___}"
(Countless technically correct answers)

**Good:** "Economic relations were difficult under the Articles because they granted no power to {regulate commerce}"

### Skip Yes/No Questions
They're harder to retain and less informative.

**Bad:** "Is segmentation used on modern processors?"
**Good:** "Segmentation was removed starting with the {{x86-64}} platform"

### Make Questions Context-Free
Cards should be comprehensible without surrounding material:
- State the topic upfront ("AWS:", "Python:")
- Avoid "What does the textbook say about X?"

**Source:** [Control-Alt-Backspace - Rules for Designing Precise Anki Cards](https://controlaltbackspace.org/precise/)

---

## The "EAT" Framework

A simplified approach to the 20 rules:

### E - Encoded
**Learn before you memorize.** Only create cards from material you've already understood. Anki schedules practice; it doesn't create understanding.

### A - Atomic
**One concept per card.** Keep questions specific and focused. Vague questions slow recall.

**Bad:** "Describe Unipolar Junction Transistors"
**Good:** "Where does the p-n junction of the UJT form?"

### T - Timeless
**Write for your future self.** Use clear language and sufficient context so cards remain understandable months later.

**Source:** [LeanAnki - How to Make Better Anki Cards](https://leananki.com/creating-better-flashcards/)

---

## Card Type Selection Guide

### Basic Cards
Best for:
- Definitions
- Single facts
- Direct Q&A
- Terminology

### Cloze Deletion
Best for:
- Fill-in-the-blank recall
- Sequences and processes
- Relationships between concepts
- Converting textbook sentences directly

### Type-In Cards
Best for:
- Precise terminology
- Spellings
- Exact recall requirements (chemical formulas, etc.)

### Avoid "Basic (and reversed card)"
Creates unnecessary review overhead. If you need both directions, create two separate cards with intentionally different wording.

---

## Quality Checklist

Before creating any card, ask:

- [ ] **Atomic?** Does this test ONE clear concept?
- [ ] **Unambiguous?** Is there exactly one correct answer?
- [ ] **Context-free?** Can this be understood without other materials?
- [ ] **Concise?** Is the answer as short as possible while complete?
- [ ] **Understood?** Do I actually understand this, or am I just memorizing?

### Red Flags

- Answer contains "and" connecting separate facts → **Split it**
- Multiple bullet points in answer → **Split it**
- Copy-pasted paragraph → **Rewrite and atomize**
- Question is vague ("What is X?") → **Make it specific**
- Answer requires a list → **Convert to cloze or separate cards**

---

## The Pleasure Test

From Wozniak: **"A simple and universal litmus test for good formulation is the pleasure of learning."**

If reviewing feels like a chore:
- Check for rule violations
- Cards may be too long, ambiguous, or poorly worded
- Understanding may be missing (Rule #1 violated)

Good cards should feel satisfying to answer correctly.

---

## Creating Cards from Textbooks

### Workflow
1. **Read and understand first** - Never create cards during first reading
2. **Identify key concepts** - Definitions, principles, relationships, comparisons
3. **Plan coverage** - Decide what merits a card vs. what's context
4. **Draft cards** - Apply minimum information principle
5. **Review and refine** - Check against quality criteria

### What Deserves a Card

- Core definitions you need to recall
- Key principles and frameworks
- Decision criteria and evaluation questions
- Common antipatterns to avoid
- Precise terminology

### What Does NOT Deserve a Card

- Extended examples (context, not recall)
- Tool-specific implementation details (outdated quickly)
- Paragraph-length explanations (not atomic)
- Obvious facts or common knowledge
- Information easily looked up when needed

---

## Additional Resources

### Primary Sources
- [SuperMemo - Twenty Rules of Formulating Knowledge](https://www.supermemo.com/en/blog/twenty-rules-of-formulating-knowledge) - The original and most authoritative guide
- [SuperMemo.guru - 20 Rules Wiki](https://supermemo.guru/wiki/20_rules_of_knowledge_formulation) - Updated version with additional context

### Practical Guides
- [Control-Alt-Backspace - Rules for Designing Precise Anki Cards](https://controlaltbackspace.org/precise/) - Practical examples of good vs. bad cards
- [LeanAnki - Creating Better Flashcards](https://leananki.com/creating-better-flashcards/) - The EAT framework and workflow tips
- [Ness Labs - The Power of Spaced Repetition](https://nesslabs.com/spaced-repetition) - Overview of the science

### Research
- [Kornell (2009) - Spacing Is More Effective Than Cramming (PDF)](https://web.williams.edu/Psychology/Faculty/Kornell/Publications/Kornell.2009b.pdf)
- [Wikipedia - Spaced Repetition](https://en.wikipedia.org/wiki/Spaced_repetition) - History and research overview
- [PMC - Spaced Repetition Flashcards for Medical Education](https://pmc.ncbi.nlm.nih.gov/articles/PMC8368120/)

---

*Last updated: 2026-02-02*
