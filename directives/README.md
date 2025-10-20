# Directives Directory

This directory contains all the directive files used by XSArena for various purposes. The structure is organized as follows:

## Directory Structure

- `base/` - Core templates and foundational directives (e.g., zero2hero, basic templates)
- `style/` - Style overlays and formatting directives (e.g., narrative, no_bs, compressed)
- `roles/` - Role-based prompts (100+ different roles for various use cases)
- `prompt/` - Structured prompts for specific tasks
- `profiles/` - Preset combinations of directives for common workflows
- `system/` - System-level prompts and instructions
- `_rules/` - CLI agent rules and guidelines
- `manifest.yml` - Index of all directives

## Purpose

Directives provide a way to customize and control the behavior of AI models by providing specific instructions, templates, or context. They are used throughout the XSArena system to guide content generation, role-playing, and other AI-driven tasks.

## Usage

Directives can be referenced by name in various parts of the system to apply specific behaviors or styles to AI interactions. The manifest.yml file provides a complete index of all available directives.
