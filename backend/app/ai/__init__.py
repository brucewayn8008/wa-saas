"""AI layer — prompt building + LLM calls only.

Boundary rule (see AGENTS.md / architecture.md): `ai/` NEVER sends a WhatsApp
message and NEVER touches transport. It builds prompts (`persona.py`), calls an
LLM (`provider.py`), and runs the qualify→propose→confirm pipeline (`pipeline.py`).
The caller (`tasks/`) is responsible for the compliance gate and for delivering
the reply through a `MessagingProvider`.
"""
