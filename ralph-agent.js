#!/usr/bin/env node
/**
 * Ralph Agent for Estate Sales Notifier
 * 
 * A simple autonomous coding agent for this Python project.
 * Based on the Ralph Wiggum technique (continuous autonomy).
 * 
 * Usage:
 *   node ralph-agent.js "Your task description"
 *   node ralph-agent.js "Add error handling for network timeouts"
 * 
 * Set ANTHROPIC_API_KEY in environment or .env file.
 */

import 'dotenv/config';
import { RalphLoopAgent, iterationCountIs } from 'ralph-loop-agent';
import { tool } from 'ai';
import { z } from 'zod';
import * as fs from 'fs/promises';
import * as path from 'path';
import { execSync } from 'child_process';

const PROJECT_DIR = process.cwd();

// Simple file operations tools
const tools = {
  listFiles: tool({
    description: 'List files in a directory (glob pattern supported)',
    parameters: z.object({
      pattern: z.string().optional().describe('Glob pattern, e.g., "*.py" or "**/*.py"'),
    }),
    execute: async ({ pattern }) => {
      try {
        const cmd = pattern 
          ? `find . -name "${pattern}" -type f | head -50`
          : `find . -maxdepth 2 -type f | head -50`;
        const output = execSync(cmd, { cwd: PROJECT_DIR, encoding: 'utf-8' });
        return { files: output.trim().split('\n').filter(Boolean) };
      } catch (error) {
        return { error: error.message };
      }
    },
  }),

  readFile: tool({
    description: 'Read contents of a file',
    parameters: z.object({
      filePath: z.string().describe('Path to the file'),
      lineStart: z.number().optional().describe('Start line (1-indexed)'),
      lineEnd: z.number().optional().describe('End line (inclusive)'),
    }),
    execute: async ({ filePath, lineStart, lineEnd }) => {
      try {
        const fullPath = path.join(PROJECT_DIR, filePath);
        const content = await fs.readFile(fullPath, 'utf-8');
        
        if (lineStart && lineEnd) {
          const lines = content.split('\n');
          const selectedLines = lines.slice(lineStart - 1, lineEnd);
          return { content: selectedLines.join('\n'), totalLines: lines.length };
        }
        
        return { content, totalLines: content.split('\n').length };
      } catch (error) {
        return { error: error.message };
      }
    },
  }),

  writeFile: tool({
    description: 'Write content to a file (creates directories if needed)',
    parameters: z.object({
      filePath: z.string().describe('Path to the file'),
      content: z.string().describe('Content to write'),
    }),
    execute: async ({ filePath, content }) => {
      try {
        const fullPath = path.join(PROJECT_DIR, filePath);
        await fs.mkdir(path.dirname(fullPath), { recursive: true });
        await fs.writeFile(fullPath, content, 'utf-8');
        return { success: true, filePath };
      } catch (error) {
        return { success: false, error: error.message };
      }
    },
  }),

  editFile: tool({
    description: 'Edit a file by replacing specific text (search and replace)',
    parameters: z.object({
      filePath: z.string().describe('Path to the file'),
      oldText: z.string().describe('Exact text to find (must be unique)'),
      newText: z.string().describe('Text to replace it with'),
    }),
    execute: async ({ filePath, oldText, newText }) => {
      try {
        const fullPath = path.join(PROJECT_DIR, filePath);
        let content = await fs.readFile(fullPath, 'utf-8');
        
        const occurrences = (content.match(new RegExp(oldText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
        
        if (occurrences === 0) {
          return { success: false, error: 'Text not found in file' };
        }
        if (occurrences > 1) {
          return { success: false, error: `Text appears ${occurrences} times (must be unique)` };
        }
        
        content = content.replace(oldText, newText);
        await fs.writeFile(fullPath, content, 'utf-8');
        
        return { success: true, filePath };
      } catch (error) {
        return { success: false, error: error.message };
      }
    },
  }),

  runCommand: tool({
    description: 'Execute a shell command in the project directory',
    parameters: z.object({
      command: z.string().describe('Shell command to execute'),
    }),
    execute: async ({ command }) => {
      try {
        const output = execSync(command, {
          cwd: PROJECT_DIR,
          encoding: 'utf-8',
          maxBuffer: 10 * 1024 * 1024,
        });
        return { success: true, output: output.trim() };
      } catch (error) {
        return { success: false, error: error.message, stderr: error.stderr?.toString() };
      }
    },
  }),

  markComplete: tool({
    description: 'Mark the task as complete',
    parameters: z.object({
      summary: z.string().describe('Summary of what was accomplished'),
      filesModified: z.array(z.string()).describe('List of files modified'),
    }),
    execute: async ({ summary, filesModified }) => {
      return { complete: true, summary, filesModified };
    },
  }),
};

// Get task from command line
const taskPrompt = process.argv.slice(2).join(' ');

if (!taskPrompt) {
  console.error('Usage: node ralph-agent.js "Your task description"');
  console.error('Example: node ralph-agent.js "Add type hints to all functions"');
  process.exit(1);
}

if (!process.env.ANTHROPIC_API_KEY) {
  console.error('Error: ANTHROPIC_API_KEY environment variable not set');
  console.error('Get your API key from: https://console.anthropic.com/');
  process.exit(1);
}

console.log('╔════════════════════════════════════════════════════════╗');
console.log('║     Ralph Agent - Estate Sales Notifier Project       ║');
console.log('╚════════════════════════════════════════════════════════╝\n');
console.log(`Task: ${taskPrompt}\n`);

// Read AGENTS.md if it exists
let agentsInstructions = '';
try {
  agentsInstructions = await fs.readFile(path.join(PROJECT_DIR, 'AGENTS.md'), 'utf-8');
} catch {
  // No AGENTS.md, that's okay
}

const baseInstructions = `You are an expert software engineer working on the Estate Sales Notifier Python project.

Your task is to make code changes to complete the user's request. Work autonomously until the task is done.

When you're finished, call the markComplete tool with a summary of what you did.

${agentsInstructions ? '## Project-Specific Instructions\n\n' + agentsInstructions : ''}`;

// Create the agent
const agent = new RalphLoopAgent({
  model: 'anthropic/claude-sonnet-4',
  instructions: baseInstructions,
  tools,
  stopWhen: iterationCountIs(15),
  verifyCompletion: async ({ result }) => {
    // Check if markComplete was called
    for (const step of result.steps || []) {
      for (const toolResult of step.toolResults || []) {
        if (toolResult.toolName === 'markComplete') {
          return { 
            complete: true, 
            reason: toolResult.result?.summary || 'Task marked complete' 
          };
        }
      }
    }
    return { complete: false, reason: 'Continue working' };
  },
  onIterationStart: ({ iteration }) => {
    console.log(`\n━━━ Iteration ${iteration} ━━━`);
  },
  onIterationEnd: ({ iteration, duration, result }) => {
    console.log(`✓ Iteration ${iteration} complete (${Math.round(duration)}ms)`);
    console.log(`  Tokens: ${result.usage?.totalTokens || 0}`);
  },
});

// Run the agent
try {
  const result = await agent.loop({ prompt: taskPrompt });
  
  console.log('\n╔════════════════════════════════════════════════════════╗');
  console.log('║                    TASK COMPLETE                       ║');
  console.log('╚════════════════════════════════════════════════════════╝\n');
  console.log(`Iterations: ${result.iterations}`);
  console.log(`Reason: ${result.completionReason}`);
  console.log(`\nFinal output:\n${result.text}`);
  console.log(`\nTotal tokens: ${result.totalUsage?.totalTokens || 0}`);
} catch (error) {
  console.error('\n❌ Error:', error.message);
  process.exit(1);
}
