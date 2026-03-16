# AGENTS.md

This document provides guidelines for AI coding agents working in this repository.

## Project Overview

This is a local AI-powered RPG engine project (inspired by Old Greg's Tavern / AI Dungeon). The goal is to create a structured game engine that runs on top of LLMs with:
- Persistent game state (stats, inventory)
- Dice roll mechanics that affect narration
- Lorebook/World info injection system
- Memory and summarization for long campaigns

**Target Configuration**: 8GB VRAM, 32GB RAM

## Build/Lint/Test Commands

This project is in early planning stage. Once code is added:

### Node.js/TypeScript (Frontend/API)
```bash
npm install          # Install dependencies
npm run dev          # Development server
npm run build        # Production build
npm run lint         # Run linter
npm run typecheck    # Type checking
npm test             # Run all tests
npm test -- <file>   # Run single test file
```

### Python (Backend/ML utilities)
```bash
pip install -r requirements.txt    # Install dependencies
ruff check .                       # Lint
ruff format .                      # Format
pytest                             # Run all tests
pytest tests/test_file.py          # Run single test file
pytest tests/test_file.py -k "test_name"  # Run single test
```

## Project Structure (Planned)

```
mon-rpg-ia/
├── modeles/           # GGUF model files
├── lore/              # World data (JSON)
│   ├── personnages/
│   ├── lieux/
│   └── objets/
├── historique/        # Session logs (JSONL)
├── regles/            # Game rules (Markdown/JSON)
└── config/            # Settings files
```

## Code Style Guidelines

### General Principles
- Write documentation in French (main project language) or English for technical code
- Keep files focused and single-purpose
- Use meaningful, descriptive names over abbreviations
- Prefer explicit over implicit behavior

### Imports
- Group imports: standard library → third-party → local
- Use absolute imports for clarity
- Sort imports alphabetically within each group
- Remove unused imports before committing

### Formatting

**TypeScript/JavaScript:**
- Indent: 2 spaces
- Semicolons: optional (be consistent within files)
- Quotes: single for strings, double for JSON
- Max line length: 100 characters
- Trailing commas in multi-line structures

**Python:**
- Follow PEP 8
- Use `ruff` for formatting
- Max line length: 88 characters (Black default)
- Type hints required for function signatures

**JSON:**
- Indent: 2 spaces
- Keep files readable; split large objects into multiple files if needed

### Types (TypeScript)
- Avoid `any`; use `unknown` when type is uncertain
- Prefer interfaces for object shapes
- Use type unions for finite sets of values
- Define strict types for game entities (Character, Item, Location, etc.)

```typescript
// Good
interface Character {
  id: string;
  name: string;
  stats: CharacterStats;
  inventory: Item[];
}

type DiceRoll = D4 | D6 | D8 | D10 | D12 | D20 | D100;
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | kebab-case | `character-manager.ts` |
| Classes | PascalCase | `LorebookEntry` |
| Functions | camelCase | `injectLoreEntry()` |
| Constants | SCREAMING_SNAKE | `MAX_CONTEXT_TOKENS` |
| JSON keys | snake_case | `max_context_tokens` |
| Game entities | PascalCase | `Lieux`, `Personnage` |

### Error Handling
- Use custom error classes for domain errors
- Provide helpful error messages with context
- Log errors with enough detail for debugging
- Graceful degradation: game should not crash on invalid input

```typescript
// Good
throw new ValidationError(
  `Invalid character stats: HP (${hp}) exceeds maximum (${maxHp})`
);
```

### Comments
- NO comments unless explicitly requested
- Code should be self-documenting
- Complex business logic (game rules) may warrant brief inline explanations

### Game-Specific Patterns

**Lorebook Entries:**
```json
{
  "key": ["excalibur", "épée légendaire"],
  "content": "Description...",
  "priority": 800,
  "order": 100,
  "trigger_chance": 100
}
```

**Character State:**
```json
{
  "id": "char_001",
  "name": "Aldric",
  "hp": { "current": 45, "max": 60 },
  "inventory": ["sword_iron", "potion_health"],
  "active_quests": ["quest_001"]
}
```

**Dice Rolls:**
- Always log rolls with context
- Store results for potential replay/verification
- Format: `{ dice: "d20", result: 15, modifier: 2, total: 17 }`

### Git Commit Guidelines
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Write commit messages in French or English (be consistent)
- Reference game features in commits (e.g., `feat: add inventory persistence`)

### Testing Strategy
- Unit tests for game logic (dice rolls, stat calculations)
- Integration tests for data flow (lore injection, state updates)
- Mock LLM responses for deterministic testing
- Test edge cases: zero values, empty inventories, missing lore

### Performance Considerations
- Context window is precious; optimize injected content size
- Lazy-load lore entries; avoid loading entire world at once
- Cache computed values (stat modifiers, etc.)
- Use streaming for LLM responses when possible

## Key Concepts

### Context Injection Priority
Higher priority = injected later in context = better remembered by LLM.

| Priority | Usage |
|----------|-------|
| 1000 | Absolute rules (cannot be broken) |
| 800 | Player stats, active quest state |
| 600 | Active scene, present NPCs |
| 400 | Background lore, world history |
| 200 | Ambient details, descriptions |

### Memory Categories
- **Constant**: Always in context (player name, core rules)
- **Conditional**: Triggered by location, state, time
- **Actor**: Active only when NPC is present
- **Summary**: Condensed session history

## When Adding Code

1. Create appropriate directory structure first
2. Initialize `package.json` (Node) or `requirements.txt` (Python)
3. Add linter/formatter config (`.prettierrc`, `ruff.toml`)
4. Write tests alongside new features
5. Update documentation (README sections, inline docs for complex logic)