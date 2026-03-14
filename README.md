<a name="readme-top"></a>
<!-- PROJECT LOGO -->
<br />
<div align="center">
<img src="https://github.com/vertex-ai-automations/pylogshield/raw/main/docs/img/pylogshield.png" alt="PyLogShield Logo" width="150">
<p>
<br>
<strong>📃
<a href="https://vertex-ai-automations.github.io/pylogshield"><strong>Examples and Docs</strong></a>
|🔧
<a href="https://github.com/vertex-ai-automations/pylogshield/issues/new">Report Bug/Issues</a>
|⛪
<a href="https://www.vertexaiautomations.com">Vertex AI Automations</a>|
</p>
<br>
<img src="docs/img/pylogshield_animate.gif" alt="PyLogShield Animation">
<br>
</div>

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Quick Start](#-quick-start)
  - [Installation](#-installation)
- [Contributing](#-contributing)


## 📣 Overview
A Python logging library designed for data professionals and developers who need reliable, secure logging with minimal setup. It extends Python's standard `logging` module with production-ready features commonly needed in data engineering and application development. It includes features like sensitive data masking, log rotation, asynchronous logging, rate limiting, and dynamic configuration, all while remaining lightweight and easy to use.

<!-- Features -->
## 💡 Features

- **Sensitive Data Masking**: Automatically masks predefined sensitive fields (e.g., `password`, `token`) in logs.
- **Log Filtering**: Filter logs based on specific keywords.
- **Dynamic Masking Control**: Enable or disable masking on a per-log basis using the `mask` parameter.
- **Performance Metrics**: Track logs per second for insights into logging activity.
- **Interactive Log Viewer**: View logs in a structured, styled table using the `rich` library.
- **Rate Limiting**: Avoid repetitive logs of the same message within a specified interval.
- **Log Rotation**: Supports rotating log files based on file size, with configurable backup counts.
- **Asynchronous Logging**: Offload logging to a background thread for improved performance.
- **JSON Log Formatting**: Optional structured JSON logging for integration with log aggregation tools.
- **Dynamic Log Level Adjustments**: Update logger settings (e.g., log level) dynamically at runtime.
- **Reusable Global Logger**: Easily access a shared logger across multiple modules with `get_logger`.
- **Color-Coded Logs**: Enable `rich` integration for visually enhanced terminal output.
- **CLI Log Viewer (Static/Live)**: Log viewer using CLI, also supports live viewer and detects for changes.
- **Custom Log Level**: Runtime custom log level injection (e.g. `SECURITY`, `AUDIT`)

<!-- GETTING STARTED -->
## 📌 Quick Start

### Installation

Install:
```bash
pip install pylogshield
```
Upgrade:
```bash
pip install --upgrade pylogshield
```

**Documentation**

Full developer docs with API reference, usage, and model schema:

- 👉 [Docs and Examples (PyLogShield)](https://vertex-ai-automations.github.io/pylogshield)

<!--Contributors-->


## 👪 Contributing
All contributions are welcome. If you have a suggestion that would make this better, please fork the repo and create a merge request. You can also simply open an issue with the label 'enhancement'.

Don't forget to give the project a star! Thanks again!

 🔶 [View all contributors](https://github.com/vertex-ai-automations/pylogshield/graphs/contributors)
 

<p align="right">(<a href="#readme-top">back to top</a>)</p>
