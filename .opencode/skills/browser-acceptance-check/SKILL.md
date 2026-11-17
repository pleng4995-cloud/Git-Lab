---
name: browser-acceptance-check
description: Check a running local BJT bias web app in a real browser using student-provided acceptance cases and expected results.
---

1. Get the running local URL and the student's A1–A5 case table.
   Ask for any missing inputs or expected results before judging a case.
2. Prefer Playwright MCP if connected. Use an available browser tool to
   navigate to the local URL, and name the tool actually used. For each case,
   select the mode, fill the relevant fields and submit. Read the actual
   values, units, visible field states or validation message from the page.
3. Compare observations against the student's expectations and tolerance.
   Report case ID, method, expected result, observed result and PASS or FAIL.
   Mark any unexecuted or unobservable case NOT RUN and explain the blocker.
4. Report evidence from the browser, such as visible result text or a
   screenshot if available. Reading source code or sending an HTTP request
   does not count as running a browser case. Do not edit source files while
   checking. Ask before moving from reporting to fixing.
