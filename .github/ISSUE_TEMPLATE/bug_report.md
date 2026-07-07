---
name: Bug report
description: Report broken behavior in Luminesk CLI.
title: "[Bug]: "
labels:
  - bug
assignees:
  - Taskov1ch
body:
  - type: markdown
    attributes:
      value: |
        Thanks for reporting a bug. Please fill out all relevant sections so we can reproduce and fix the problem quickly.
  - type: textarea
    id: summary
    attributes:
      label: Bug summary
      description: What is wrong?
      placeholder: A short description of the bug.
    validations:
      required: true
  - type: textarea
    id: steps
    attributes:
      label: Steps to reproduce
      description: Provide exact commands and sequence.
      placeholder: |
        1. Run `nesk ...`
        2. Run `nesk ...`
        3. Observe error
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Expected behavior
      description: What did you expect to happen?
    validations:
      required: true
  - type: textarea
    id: actual
    attributes:
      label: Actual behavior
      description: What happened instead?
    validations:
      required: true
  - type: textarea
    id: logs
    attributes:
      label: Logs and diagnostics
      description: Paste output from `nesk diagnostic` and relevant command logs.
      render: shell
  - type: input
    id: os
    attributes:
      label: Operating system
      placeholder: Ubuntu 24.04 / Windows 11 / macOS 15
    validations:
      required: true
  - type: input
    id: version
    attributes:
      label: Luminesk CLI version
      placeholder: 1.0.1
    validations:
      required: true
  - type: textarea
    id: additional
    attributes:
      label: Additional context
      description: Add screenshots, links, or anything else that can help.
