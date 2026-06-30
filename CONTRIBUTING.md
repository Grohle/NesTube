# Contributing to Nestify

Thanks for your interest in improving Nestify! Bug reports, feature ideas and
pull requests are all welcome.

## Reporting issues

Open an issue at <https://github.com/Grohle/nestify/issues> with:

- What you expected to happen and what actually happened.
- Steps to reproduce (a small cut list / profile that triggers it helps a lot).
- Your OS, the Nestify version (Help → About), and any error message.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install pytest
python main.py                       # run the app
```

## Running the tests

The test suite must pass before a pull request can be merged (CI runs it on
every push). GUI tests run headlessly with Qt's offscreen platform:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

Please add or update tests for any behaviour you change.

## Pull request checklist

- [ ] The full test suite passes locally (`pytest`).
- [ ] New behaviour is covered by tests.
- [ ] Commit messages explain the *why*, not just the *what*.
- [ ] The change is focused — one logical change per pull request.

## Contributor License Agreement (CLA)

Nestify is released under the **GPL-3.0**, but the project maintainer keeps the
option of offering the software under a separate **commercial license** as well
(dual licensing). For that to remain possible, the maintainer must hold the
rights to all contributed code.

**By submitting a pull request you agree that:**

1. You are the author of the contribution (or have the right to submit it), and
2. You grant the project maintainer (Alberto Miranda) a perpetual, worldwide,
   irrevocable license to use, modify, relicense and distribute your
   contribution, **including under licenses other than the GPL-3.0** (e.g. a
   commercial license), while your contribution also remains available under the
   GPL-3.0.

This is the same model used by many dual-licensed open-source projects (e.g. Qt).
If you cannot agree to this, please open an issue to discuss before contributing.
