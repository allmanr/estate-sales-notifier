# Ralph Agent for Estate Sales Notifier

This project uses the **Ralph Wiggum Technique** - a continuous autonomy approach where an AI agent iteratively works on coding tasks until completion.

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure API key:**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

## Usage

Run the Ralph agent with a task description:

```bash
# Using npm script
npm run ralph "Add error handling for network timeouts"

# Or directly
node ralph-agent.js "Your task here"
```

### Example Tasks

```bash
# Add functionality
npm run ralph "Add a --dry-run flag that prints without sending emails"

# Refactoring
npm run ralph "Extract the email sending logic into a separate function"

# Testing
npm run ralph "Add unit tests for the distance parsing function"

# Documentation
npm run ralph "Add docstrings to all functions in estate_sales_notifier.py"

# Bug fixes
npm run ralph "Fix the issue where sales with missing addresses cause crashes"
```

## How It Works

The Ralph agent:
1. **Reads your task** and the project context from `AGENTS.md`
2. **Iterates autonomously** - reads files, makes changes, runs commands
3. **Calls `markComplete`** when done with a summary of changes
4. **Stops automatically** after completing the task or hitting iteration limit (15)

## Tools Available

The agent has access to:
- `listFiles` - Find files in the project
- `readFile` - Read file contents (with optional line ranges)
- `writeFile` - Create or overwrite files
- `editFile` - Search and replace specific text
- `runCommand` - Execute shell commands (Python scripts, tests, etc.)
- `markComplete` - Signal task completion

## Configuration

### Project Context (`AGENTS.md`)
The `AGENTS.md` file contains project-specific instructions that guide the agent:
- How to run the Python application
- Key files and their purposes
- Common tasks and commands
- Best practices for this project

Edit `AGENTS.md` to customize agent behavior.

### Agent Settings (`ralph-agent.js`)
- **Model**: `anthropic/claude-sonnet-4` (fast, cost-effective)
- **Max iterations**: 15 (prevents runaway costs)
- **Tools**: File operations + shell commands

## Cost Control

- Uses Claude Sonnet (not Opus) for lower costs
- Limited to 15 iterations maximum
- Each iteration shows token usage
- Full cost summary at completion

## Tips

- Be specific in your task descriptions
- The agent can see `AGENTS.md` and will follow project conventions
- It will call `markComplete` when done - look for the summary
- Check the files it modified after completion
- Start simple, then try more complex multi-step tasks

## Comparison to Manual Coding

Instead of manually:
1. Reading files to understand the code
2. Making changes across multiple locations
3. Testing your changes
4. Documenting what you did

The Ralph agent does all of this autonomously in one command.
