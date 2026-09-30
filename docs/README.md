# HealthPro documentation

Personal nutrition tracker. React frontend, FastAPI backend, local JSON storage. Nutrient numbers come from food tables. A language model is used only for language tasks.

| Document | Purpose |
|---|---|
| [Project Proposal](01-Project-Proposal.md) | Why the project exists, scope, and approach |
| [Project Synopsis](02-Project-Synopsis.md) | Short description suitable for an abstract or cover note |
| [Software Requirements Specification](03-Software-Requirements-Specification.md) | Functional and non-functional requirements |
| [High-Level Design](04-High-Level-Design.md) | Components, data flow, and major decisions |
| [Low-Level Design](05-Low-Level-Design.md) | Modules, data shapes, algorithms, and APIs |
| [Final Project Report](06-Final-Project-Report.md) | What was built, how it was verified, and what remains |
| [User Manual](07-User-Manual.md) | How to install, start, and use each page |
| [Test Plan](08-Test-Plan.md) | Checks for the main flows and known limits |
| [HealthPro.pptx](HealthPro.pptx) | Presentation of the application |

Regenerate the deck with `..\.venv\Scripts\python.exe docs\build_presentation.py` after `pip install python-pptx` in the project virtual environment. That package is used only to build the slides. It is not part of the application runtime.

Version 0.1.0. Educational personal tracker, not medical advice.
