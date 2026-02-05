# Knowledge Base Repository Structure (Hackathon PoC)

This document defines a **simplified** KB repository structure for hackathon demonstration. Focus is on core functionality rather than complex categorization.

## Simplified Directory Structure

```
knowledge-base/
├── README.md                          # Repository overview
├── troubleshooting/                   # Problem-solving guides
│   └── example-database-issue.md     # Sample document
├── processes/                         # Standard procedures  
│   └── example-deployment-process.md # Sample document
├── decisions/                         # Technical decisions
│   └── example-tool-choice.md        # Sample document
└── .archie-generated/                 # Archie metadata (simple)
    └── last-update.json              # Basic tracking
```

## Hackathon Approach

### **Core Categories (3 only)**
1. **troubleshooting** - Problem-solving guides
2. **processes** - Standard procedures
3. **decisions** - Technical choices and rationale

### **No Complex Configuration**
- No subcategories for hackathon
- No complex YAML configuration files
- Simple file-based approach
- Focus on content generation, not structure

## Document Templates

### `.archie/templates/troubleshooting.md`
```markdown
---
title: "{TITLE}"
category: "troubleshooting"
tags: [{TAGS}]
difficulty: "intermediate"
source_type: "slack"
source_threads: [{SOURCE_THREADS}]
ai_confidence: {AI_CONFIDENCE}
ai_reasoning: "{AI_REASONING}"
created_date: "{CREATED_DATE}"
last_updated: "{TIMESTAMP}"
---

# {TITLE}

## Problem Description
{PROBLEM_DESCRIPTION}

## Environment
- **System**: {SYSTEM_INFO}
- **Version**: {VERSION_INFO}
- **Environment**: {ENVIRONMENT}

## Symptoms
{SYMPTOMS}

## Root Cause
{ROOT_CAUSE}

## Solution
{SOLUTION_STEPS}

## Prevention
{PREVENTION_MEASURES}

## Related Issues
{RELATED_LINKS}
```

### `.archie/templates/process.md`
```markdown
---
title: "{TITLE}"
category: "process"
tags: [{TAGS}]
difficulty: "intermediate"
source_type: "slack"
source_threads: [{SOURCE_THREADS}]
ai_confidence: {AI_CONFIDENCE}
ai_reasoning: "{AI_REASONING}"
created_date: "{CREATED_DATE}"
last_updated: "{TIMESTAMP}"
---

# {TITLE}

## Overview
{PROCESS_OVERVIEW}

## Prerequisites
{PREREQUISITES}

## Step-by-Step Process
{PROCESS_STEPS}

## Validation
{VALIDATION_STEPS}

## Troubleshooting
{COMMON_ISSUES}

## Related Processes
{RELATED_PROCESSES}
```

### `.archie/templates/decision.md`
```markdown
---
title: "{TITLE}"
category: "decision"
tags: [{TAGS}]
difficulty: "intermediate"
source_type: "slack"
source_threads: [{SOURCE_THREADS}]
ai_confidence: {AI_CONFIDENCE}
ai_reasoning: "{AI_REASONING}"
created_date: "{CREATED_DATE}"
last_updated: "{TIMESTAMP}"
review_date: "{REVIEW_DATE}"
---

# {TITLE}

## Context
{DECISION_CONTEXT}

## Decision
{DECISION_MADE}

## Rationale
{REASONING}

## Alternatives Considered
{ALTERNATIVES}

## Consequences
### Positive
{POSITIVE_CONSEQUENCES}

### Negative
{NEGATIVE_CONSEQUENCES}

## Implementation Notes
{IMPLEMENTATION}
```

## Repository README Template

```markdown
# {TEAM_NAME} Knowledge Base

This repository contains the living knowledge base for {TEAM_NAME}, automatically maintained by [Archie](https://github.com/your-org/archie).

## 📚 Contents

- **[Troubleshooting](troubleshooting/)** - Problem-solving guides and solutions
- **[Processes](processes/)** - Standard operating procedures  
- **[Decisions](decisions/)** - Architecture and technical decisions

## 🤖 About Archie

This knowledge base is automatically generated and maintained by Archie, which:

- Extracts knowledge from Slack conversations
- Identifies valuable troubleshooting, processes, and decisions
- Generates structured documentation
- Keeps content up-to-date through living updates

## 📋 How to Use

1. **Browse by Category**: Navigate to the relevant category folder
2. **Search**: Use GitHub's search functionality to find specific topics
3. **Contribute**: Knowledge is primarily extracted from Slack, but manual contributions are welcome
4. **Updates**: Most updates come through automated PRs from Archie

## 🔄 Update Process

1. Archie monitors configured Slack channels
2. Extracts knowledge-worthy conversations
3. Generates or updates documentation
4. Creates pull requests for review
5. Team reviews and merges updates

## 📊 Repository Stats

- **Total Documents**: {DOCUMENT_COUNT}
- **Categories**: {CATEGORY_COUNT}
- **Last Updated**: {LAST_UPDATE}
- **Confidence Level**: {AVERAGE_CONFIDENCE}

## ⚙️ Configuration

This repository uses a simplified configuration approach - no complex configuration files are needed. Archie automatically detects and processes content based on the defined categories and templates.
```

## File Naming Conventions

### General Rules
- Use lowercase with hyphens: `database-connection-issues.md`
- Be descriptive but concise
- Include key terms for searchability
- Avoid spaces, use hyphens instead

### Category-Specific Naming
- **Troubleshooting**: `{problem-area}-{specific-issue}.md`
  - Example: `database-connection-timeout.md`
- **Processes**: `{process-type}-{specific-process}.md`
  - Example: `deployment-staging-process.md`
- **Decisions**: `{decision-area}-{decision-topic}.md`
  - Example: `architecture-microservices-adoption.md`

## Metadata Standards

Each document should include frontmatter metadata:

```yaml
---
title: "Database Connection Timeout Issues"
category: "troubleshooting"
tags: ["database", "connection", "timeout", "performance"]
difficulty: "intermediate"
created_date: "2024-01-15"
last_updated: "2024-01-20"
source_type: "slack"
source_threads: ["slack-123", "slack-456"]
ai_confidence: 0.89
ai_reasoning: "Thread contains detailed troubleshooting steps with verified solution"
---
```

This structure provides a scalable, maintainable foundation for living knowledge bases that can grow and evolve with your team's needs.