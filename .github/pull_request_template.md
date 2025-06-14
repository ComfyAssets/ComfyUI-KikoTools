## Description

<!-- Provide a brief description of the changes in this PR -->

## Type of Change

<!-- Mark the relevant option with an [x] -->

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New tool (new ComfyAssets tool implementation)
- [ ] 🚀 Enhancement (improvement to existing tool)
- [ ] 📚 Documentation update
- [ ] 🔧 Refactoring (no functional changes)
- [ ] 🧪 Tests (adding or updating tests)
- [ ] 🔄 CI/CD changes

## Changes Made

<!-- List the specific changes made -->

- [ ] Added/modified core logic in `logic.py`
- [ ] Created/updated ComfyUI node in `node.py`
- [ ] Updated base classes or shared utilities
- [ ] Added comprehensive tests
- [ ] Updated documentation
- [ ] Added example workflows

## Tool Information (if applicable)

<!-- For new tools or tool modifications -->

- **Tool Name**:
- **Category**: ComfyAssets
- **Primary Use Case**:
- **Input Types**:
- **Output Types**:

## Testing

<!-- Describe the tests you ran and their results -->

- [ ] All existing tests pass
- [ ] New unit tests added and pass
- [ ] Integration tests pass
- [ ] Manual testing completed in ComfyUI-like environment
- [ ] Tested with various input sizes and edge cases

### Test Results

```
# Paste test output here
```

## Performance Impact

<!-- Describe any performance implications -->

- [ ] No performance impact
- [ ] Performance improvement: [describe]
- [ ] Potential performance impact: [describe and justify]
- [ ] Memory usage: [no change/reduced/increased - explain why]

## Code Quality

<!-- Confirm code quality standards are met -->

- [ ] Code follows project style guidelines (black, flake8)
- [ ] Type hints added for all new functions
- [ ] Docstrings added for all public functions/classes
- [ ] No hardcoded values or secrets
- [ ] Error handling implemented appropriately

## Breaking Changes

<!-- Mark if this introduces breaking changes -->

- [ ] No breaking changes
- [ ] Breaking changes (describe below and update CHANGELOG)

### Breaking Changes Description

<!-- If breaking changes, describe what breaks and migration path -->

## Documentation

<!-- Documentation updates -->

- [ ] README.md updated (if needed)
- [ ] Tool documentation added/updated in `examples/documentation/`
- [ ] Example workflows added/updated in `examples/workflows/`
- [ ] Comments added to complex code sections

## Dependencies

<!-- New dependencies or changes -->

- [ ] No new dependencies
- [ ] New dependencies added to `requirements-dev.txt`
- [ ] Dependencies justified and minimal

### New Dependencies

<!-- List any new dependencies and justify their inclusion -->

## Architecture Compliance

<!-- Confirm adherence to project architecture -->

- [ ] Follows separation of concerns (logic.py vs node.py)
- [ ] Inherits from ComfyAssetsBaseNode
- [ ] Implements proper ComfyUI interface (INPUT_TYPES, etc.)
- [ ] Uses shared utilities where appropriate
- [ ] Follows SOLID principles

## Screenshots/Examples

<!-- Add screenshots or examples demonstrating the changes -->

### Before

<!-- If applicable, show the state before changes -->

### After

<!-- Show the result of your changes -->

## Related Issues

<!-- Link any related issues -->

Fixes #[issue_number]
Related to #[issue_number]

## Checklist

<!-- Final checklist before requesting review -->

- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Additional Notes

<!-- Any additional information for reviewers -->

## For Maintainers

<!-- This section is for maintainer use -->

- [ ] Code review completed
- [ ] Architecture review completed
- [ ] Testing verified
- [ ] Documentation review completed
- [ ] Ready for merge
