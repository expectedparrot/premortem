# Premortem Wrap-Up Guide

Use this guide when the analysis is finished and you are handing the
premortem back to the user. Run `premortem agent-end` to load it.

The user has just spent time on a structured exercise. The hand-off is where
good analysis quietly turns into "huh, neat" instead of action. Your job here
is to make the result usable.

## Instructions To The Agent

- Treat the wrap-up as its own phase. The work is not finished when the report
  file is written; it is finished when the user knows what to do with it.
- Write the chat-side summary yourself. Do not just point the user at
  `report.html` and leave.
- Lead with the recommendation. Bury caveats below, not above.
- Label the recommendation as a model output, not a verdict. The user owns the
  decision.
- Name unresolved research questions explicitly as the user's homework. Do not
  let them disappear into the report.
- If the analysis surfaced a confident "no", say so plainly. If it surfaced a
  conditional "yes", spell out the conditions.
- Offer a follow-up only if it is concrete and time-bound. Avoid vague
  "happy to help further" closers.

## What To Send The User In Chat

Keep the chat-side wrap-up tight. Aim for the following sections, in order:

1. **Bottom-line recommendation.** One or two sentences. Plain language. No
   hedging.
2. **The two or three things that drove the recommendation.** Not the full
   causal graph. The dominant mechanisms.
3. **What would have to change for the recommendation to flip.** This is what
   the research agenda is for. Surface the highest-leverage tests, not all of
   them.
4. **Where the canonical artifacts live.** The report file path, and a one-line
   note on what is in it that is not in the chat summary.
5. **Optional follow-up offer.** Only if there is a concrete next step the user
   is likely to want (for example, schedule a check-in once a research
   question has data).

## Framing The Recommendation

Premortems are decision aids, not decisions. Frame accordingly:

- Use language like "the analysis points to" or "based on the failure paths
  surfaced" rather than "you should not".
- When the analysis is lopsided enough that hedging would be dishonest, say so
  plainly and explain why the lopsidedness is real, not a quirk of the model.
- If the user is the protagonist in the failure scenarios (their decision,
  their household, their company), be careful with tone. The point is to
  illuminate failure paths they can act on, not to render judgement on them.
- If personas surfaced uncomfortable self-criticism that the user might
  recognize as themselves, do not dwell on it. Surface it once, then move to
  what to do about it.

## Handling Unresolved Research Questions

The research agenda is the most actionable artifact in the entire premortem.
Treat it as the user's homework list:

- Pull out the two or three highest-leverage tests. Specify the threshold that
  flips the decision.
- For each, name a plausible owner and a rough timeframe. If the user is the
  only owner, say so.
- If a research question depends on a third party (insurer, vendor, partner),
  flag it as a blocker that should be resolved before the others.
- Do not list every research question in chat. Point at the report for the
  full set.

## When The Report Matters Vs. When Chat Is Enough

- For lightweight analyses (small personal decision, small team initiative),
  the chat summary plus the executive summary is usually enough. Mention the
  report once and move on.
- For analyses that will be shared with stakeholders who were not in the
  conversation (a board, a partner, a manager), point at the report as the
  canonical artifact and suggest the user review it before sharing.
- If the analysis produced a strong "do not proceed" recommendation, the
  report is the document the user will want to refer back to if they revisit
  the decision later. Note that explicitly.

## What To Avoid

- Do not restate the entire executive summary in chat. The user already saw
  the artifacts roll by.
- Do not hedge a clear recommendation into mush. If the failure paths
  converge, say they converge.
- Do not invent confidence the analysis does not support. If a stakeholder
  type was missing, name the gap.
- Do not propose new mitigations or research questions in the wrap-up that
  were not surfaced in the analysis. Wrap-up summarizes; it does not extend.
- Do not close with "let me know if you have questions". Close with a
  concrete next step or with silence.

## Handing Off The Decision

The premortem ends with the user, not with you. Make sure they leave the
conversation with:

- A clear recommendation they can accept, reject, or modify.
- A short list of things to find out before deciding (or before launching, if
  the recommendation is conditional).
- The location of the canonical artifacts.
- An understanding that the analysis was prospective hindsight, not
  prophecy. The failure scenarios are plausible mechanisms, not predictions.
