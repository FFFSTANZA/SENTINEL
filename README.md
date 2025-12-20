# Senytl

Senytl provides deterministic, fast testing primitives for LLM agents, designed to run reliably in local development and CI.

## Install

```bash
pip install senytl
```

Optional extras:

```bash
pip install "senytl[pytest]"    # convenience extra (installs pytest)
pip install "senytl[semantic]"  # semantic similarity assertions (sentence-transformers + torch)
```

## Quick start (pytest)

```python
import pytest
from senytl import expect


def my_agent(prompt: str) -> str:
    return f"Hello! You said: {prompt}"


@pytest.mark.senytl_agent
def test_my_agent(senytl_agent):
    wrapped = senytl_agent(my_agent)
    response = wrapped.run("Hello!")

    expect(response).to_contain("Hello")
```

## CLI

```bash
senytl --help
senytl version
senytl suggest-tests
```

## License

MIT (see [LICENSE](LICENSE)).