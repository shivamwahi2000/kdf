# Contributing to KDF

Thank you for considering contributing to KDF! This document provides guidelines for contributing.

## Ways to Contribute

- **Report Bugs**: Open an issue describing the bug
- **Suggest Features**: Open an issue with feature proposals
- **Fix Bugs**: Submit PRs for open bug issues
- **Add Connectors**: Implement new data source connectors
- **Add Skills**: Create new data transformation or quality skills
- **Improve Documentation**: Enhance README, guides, or examples
- **Write Tests**: Increase test coverage
- **Agent Skills**: Create new agent skill specifications

## Development Setup

### Prerequisites

- Python 3.9+
- PySpark 3.4+
- Git

### Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/kdf.git
   cd kdf
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run Tests**
   ```bash
   pytest
   ```

## Code Style

- **Formatting**: Use `black` with default settings
- **Linting**: Code must pass `ruff` checks
- **Type Hints**: Use type hints for function signatures
- **Docstrings**: Use Google-style docstrings

```python
def example_function(param1: str, param2: int) -> bool:
    """One-line summary.

    More detailed description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: Description of when this is raised
    """
    pass
```

### Format Code

```bash
black kdf/
ruff check kdf/ --fix
```

## Pull Request Process

1. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write clear, focused commits
   - Include tests for new features
   - Update documentation as needed

3. **Test Locally**
   ```bash
   pytest
   black kdf/
   ruff check kdf/
   ```

4. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   - Create PR on GitHub
   - Describe the changes clearly
   - Link any related issues

5. **Code Review**
   - Address reviewer feedback
   - Keep the PR focused and reasonably sized
   - Squash commits if requested

## Adding a Connector

Connectors enable KDF to read from data sources.

### Structure

```
kdf/connectors/your_connector/
├── __init__.py
├── connector.py
├── config.py
└── auth.py
```

### Implementation

1. **Inherit from Base**
   ```python
   from kdf.connectors.base import Connector

   class YourConnector(Connector):
       def validate_connection(self, context):
           # Implementation

       def discover_schema(self, context):
           # Implementation

       def read(self, context):
           # Implementation

       def metadata(self, context):
           # Implementation
   ```

2. **Implement Configuration**
   ```python
   from pydantic import BaseModel

   class YourConnectorConfig(BaseModel):
       # Configuration fields
   ```

3. **Register**
   ```python
   # In kdf/bootstrap.py
   connector_registry.register_connector("your_connector", YourConnector)
   ```

4. **Test**
   ```python
   # In tests/test_your_connector.py
   def test_your_connector():
       # Tests
   ```

5. **Document**
   - Add to README
   - Create usage example
   - Document configuration options

## Adding a Data Skill

Skills are reusable data transformations or checks.

### Structure

```
kdf/skills/category/your_skill.py
```

### Implementation

1. **Choose Base Class**
   - `DataSkill` for transformations
   - `QualitySkill` for validation

2. **Implement**
   ```python
   from kdf.skills.base import DataSkill

   class YourSkill(DataSkill):
       def validate_config(self):
           # Validate configuration

       def execute(self, df, context):
           # Transform DataFrame
           return df
   ```

3. **Register**
   ```python
   # In kdf/bootstrap.py
   skill_registry.register_skill("your_skill", YourSkill)
   ```

4. **Test**
   - Unit tests with mock data
   - Integration tests with real Spark

5. **Document**
   - Parameter descriptions
   - Usage examples
   - Edge cases

## Adding an Agent Skill

Agent skills guide AI agents in data engineering tasks.

### Structure

```
kdf/agents/skills/your_agent_skill/
├── SKILL.md
├── examples/
└── references/
```

### Implementation

1. **Write SKILL.md**
   - Purpose and when to use
   - Required context
   - Available tools
   - Expected behavior
   - Output format
   - Examples
   - Safety considerations
   - Permissions

2. **Provide Examples**
   - Multiple realistic scenarios
   - Input/output pairs
   - Edge cases

3. **Document Tools**
   - Which KDF tools are used
   - Tool parameters
   - Tool outputs

4. **Test with Agent**
   - Verify an AI agent can follow the skill
   - Iterate based on agent feedback

## Writing Tests

### Test Structure

```python
def test_descriptive_name():
    """Test description."""
    # Arrange
    input_data = ...

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected
```

### Coverage

- Aim for >80% coverage
- Test happy paths
- Test error conditions
- Test edge cases

### Run Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_config.py

# With coverage
pytest --cov=kdf
```

## Documentation

### README Updates

When adding features:
- Update feature list
- Add usage examples
- Update roadmap if applicable

### Code Documentation

- Docstrings for all public functions
- Comments for complex logic
- Type hints

### Examples

When adding examples:
- Place in `examples/` directory
- Include comments
- Make them runnable
- Cover common use cases

## Issue Guidelines

### Bug Reports

Include:
- KDF version
- Python version
- Spark version
- Minimal reproducible example
- Expected behavior
- Actual behavior
- Error messages/stack traces

### Feature Requests

Include:
- Use case description
- Proposed API
- Alternative approaches considered
- Willingness to implement

## Security

- Never commit credentials
- Use environment variables
- Report security issues privately to security@krianno.com
- Don't open public issues for security vulnerabilities

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

## Questions?

- Open a discussion on GitHub
- Join our community (link TBD)
- Email: contributors@krianno.com

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intent

Thank you for contributing to KDF!
