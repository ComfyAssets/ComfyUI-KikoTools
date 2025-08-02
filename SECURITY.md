# Security Policy

## Supported Versions

ComfyUI-KikoTools is actively maintained. We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of ComfyUI-KikoTools seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### How to Report

Please report security vulnerabilities by [opening a new issue](https://github.com/ComfyAssets/ComfyUI-KikoTools/issues/new) with the following:

- Use the title prefix `[SECURITY]`
- Provide a clear description of the vulnerability
- Include steps to reproduce the issue
- Specify the version(s) affected
- If possible, suggest a fix or mitigation

### What to Expect

- **Response Time**: We aim to acknowledge receipt within 48 hours
- **Investigation**: We will investigate and validate the reported vulnerability
- **Updates**: We will keep you informed about the progress
- **Resolution**: Once verified, we will work on a fix and release it as soon as possible
- **Credit**: We will acknowledge your contribution in the release notes (unless you prefer to remain anonymous)

### Scope

Security vulnerabilities in scope include:

- Code execution vulnerabilities in node implementations
- Path traversal or file system access issues
- API key or credential exposure
- Dependency vulnerabilities that affect the project
- Any issue that could compromise user data or system security

### Out of Scope

The following are generally not considered security vulnerabilities:

- Issues in ComfyUI core (report these to the ComfyUI project)
- Performance issues
- Bugs that don't have security implications
- Feature requests

## Security Best Practices

When using ComfyUI-KikoTools:

- Keep your installation up to date
- Store API keys (like Gemini API keys) securely using environment variables
- Review generated files before sharing them
- Be cautious with custom prompts that might expose sensitive information

## Contact

For urgent security matters, you can also reach out to the maintainers directly through GitHub.

Thank you for helping keep ComfyUI-KikoTools secure!
