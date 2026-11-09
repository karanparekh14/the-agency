"""The deploy gate: every check a commit must pass before it reaches the live machine.

scan     secrets and personal data never get committed
trace    every commit names who made it and why, and stays inside that author's files
drift    a live file edited outside git blocks the deploy instead of being silently overwritten
deploy   quiet windows, checks, drift guard, copy with backups, new manifest
run_tests  every offline test suite, one line each, real exit code
"""
