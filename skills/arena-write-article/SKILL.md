---
name: arena-write-article
description: >-
  Turns agent safety findings into public-facing opinion articles and explainers.
  Use when outlining, drafting, editing, or translating an article based on evaluations.
---

# Write an article from safety findings

## Find the argument

Start with the decision the reader faces. What did they ask the product to do?
What protection would they reasonably expect while it does that job? Write the
article's answer in one sentence. Test the proposed title against that sentence.
“We tested three agents” identifies a subject. “A sandbox can stop a deletion
and still leave your file exposed” gives the reader a reason to keep reading.

Match the requested stage. For an outline, give each section a reader question
and the evidence that answers it. When the author wants to review one chapter,
draft that chapter. For a light edit, keep the approved opening, argument and
examples. Change the passages the author identified.

## Give each section one job

Open with a familiar expectation, one result that challenges it, and what that
result means for the reader. Explain a technical term when it helps answer the
question the opening raises. A historical comparison earns its place when it
explains how the reader's expectation arose or how a design delivers protection.

For a claim such as “partial protection can leave data exposed,” choose the
case that tests that claim most directly. Show who acted, what changed, and
why the reader cares. Link the underlying record at the end of the paragraph.
Use additional cases when they change the conclusion or expose a different
route to the same harm. Put procedures, command output and exhaustive counts
in the linked report.

## Use the strongest claim the evidence supports

Before writing the key sentence, check the product, platform, object affected,
approval sequence and observed outcome. Keep a direct observation in the past
tense. Use conditional language for a consequence that did not occur in the
trial. Attribute earlier operator observations when a public record is missing.
Product documentation can explain a mechanism. A trial record establishes
what happened in that run.

For example, WorkBuddy preserved a protected directory in one test. In a
separate test, a program it ran gave the Windows Everyone group permission to
delete a sample file. An article can say, “The file was still there. Who could
delete it had changed.” Joining those trials into a story in which the program
retried and deleted the original directory would invent an event.

If a prompt appeared, say what it disclosed, who approved it and what the
program then did, to the extent those details affect the argument. Distinguish
approving a script from knowingly consenting to recording. Criticize the
product's promise in direct language. Claims about a vendor's intent need
evidence about that intent.

## Edit for the reader

- Replace abstract assessments with consequences a reader can picture.
  “It captured the whole desktop, including the private chat beside the
  spreadsheet” conveys more than “the isolation boundary was inadequate.”
  Mark a hypothetical chat as hypothetical when the screenshot used a fixture.
- Give each takeaway one conclusion and one concrete reason. Put the article's
  central distinction first. Read the takeaways together and cut repetition.
- End by answering the opening question. If the issue is product responsibility,
  say what the product must protect after the user clicks Allow. A fresh list
  of tests in the last paragraph distracts from that judgment.
- When translating, work from the approved edition. Check the title, takeaways
  and ending side by side for the same strength of claim. Check each example
  for the same actor, action, approval and outcome. Let the wording sound
  natural in each language.

For a worked example, read the [Chinese sandbox article](../../articles/agent-sandbox.zh-CN.md)
and its [English edition](../../articles/agent-sandbox.en.md). For a website
edition, follow the [article publication conventions](../../docs/article-library.md).
For a formal case report, use [arena-write-report](../arena-write-report/SKILL.md).
