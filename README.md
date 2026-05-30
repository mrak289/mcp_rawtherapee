# MCP Server for RawTherapee

A Model Context Protocol (MCP) server that exposes RawTherapee's photo processing capabilities to AI assistants.

## Features

- Apply processing profiles (`.pp3`) to RAW images
- Batch process images via RawTherapee CLI
- Query and manipulate processing parameters

## Requirements

- RawTherapee installed (with CLI access)
- Python 3.10+

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python src/server.py
```
