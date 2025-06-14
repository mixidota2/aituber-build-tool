# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Install dependencies with uv
uv sync --all-groups

# Install for development (includes dev dependencies)
uv sync --all-groups

# Run as module during development
uv run python -m aituber <command>
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_services.py

# Run specific test function
uv run pytest tests/test_services.py::test_llm_generate

# Run tests with async support
uv run pytest -v tests/test_services.py
```

### Linting and Type Checking
```bash
# Run ruff linter
uv run ruff check src/

# Fix linting issues
uv run ruff check --fix src/

# Run mypy type checker
uv run mypy src/aituber/
```

### Application Commands
```bash
# Initialize configuration
aituber init

# List available characters
aituber list-characters

# Start chat session
aituber chat --character railly

# Start chat with streaming
aituber chat --character railly --stream
```

## Architecture Overview

This is a modular AITuber framework built with a service-oriented architecture using dependency injection.

### Core Architecture Pattern

The application uses a **ServiceContainer** pattern (`src/aituber/core/container.py`) that manages lazy-loaded singleton services. Each service follows clear interfaces and can be easily mocked for testing.

**Key Service Dependencies:**
- `ConversationService` orchestrates `CharacterService`, `MemoryService`, and `LLMService`
- `MemoryService` (ChromaDB) depends on `LLMService` for embeddings
- `CharacterService` uses `StorageService` for YAML-based character data
- All services receive the same `AITuberConfig` instance

### Service Layer Structure

Services are organized by domain in `src/aituber/core/services/`:

- **LLM Layer** (`llm/`): Abstract base with OpenAI implementation, supports async streaming
- **Memory Layer** (`memory/`): ChromaDB vector storage with semantic search capabilities  
- **Character Layer** (`character.py`): YAML-based character management with rich persona models
- **Conversation Layer** (`conversation.py`): Main orchestration hub that coordinates all services
- **Storage Layer** (`storage/`): File system abstraction for data persistence
- **TTS Layer** (`tts_service.py`): VoiceVox integration for character-specific voice synthesis

### Data Flow in Conversations

1. User input → `ConversationService.process_message()`
2. Character loading → `CharacterService.get_character()`
3. Memory retrieval → `MemoryService.retrieve_relevant_memories()` (semantic search)
4. Prompt construction → Character prompt + memories + conversation history
5. LLM generation → `OpenAIService.generate()` or `generate_stream()`
6. Memory storage → `MemoryService.add_memory()` (stores new interaction)
7. Response delivery → CLI/API

### Configuration Management

Centralized configuration in `src/aituber/core/config.py` using Pydantic models:
- `AITuberConfig` contains nested configs for each service domain
- YAML-based configuration files with environment variable support
- Type-safe validation with clear error messages

### Character System

Characters are defined in YAML files with rich data models:
- `Character` model includes persona, personality traits, interests
- `VoicevoxConfig` for character-specific voice settings
- File-based storage in `data/characters/` directory
- Dynamic character loading and switching

### Memory System

ChromaDB-based vector memory for long-term context:
- Automatic embedding generation via LLM service
- Semantic similarity search for relevant memory retrieval
- Character-scoped memory isolation
- Configurable similarity thresholds and limits

### Testing Strategy

Tests are organized by service layer in `tests/`:
- Heavy use of `AsyncMock` for async service testing
- Dependency injection allows easy service mocking
- Fixture-based test configuration with temporary directories
- Both unit tests (individual services) and integration tests (service interactions)

### Interface Layers

**CLI Interface** (`src/aituber/interface/cli/`):
- Typer-based commands with async support
- Streaming and non-streaming chat modes
- Character management commands

**API Interface** (`src/aituber/api/`):
- FastAPI with lifespan management for service initialization
- Pydantic request/response models
- Multi-modal responses (text and audio)

## Development Guidelines

### Adding New Services

1. Create interface in appropriate service directory
2. Implement abstract base class following existing patterns
3. Add service property to `ServiceContainer`
4. Update `AITuberConfig` if configuration needed
5. Add comprehensive tests with mocking

### Character Development

- Characters are YAML files in `data/characters/`
- Use existing character models in `src/aituber/core/models/character.py`
- Include persona, personality traits, interests, and voice configuration
- Test character loading with `CharacterService`

### Memory Integration

- Memory operations are async and use embeddings
- Always scope memories to specific characters
- Use semantic search with appropriate thresholds
- Consider memory lifecycle and cleanup

### Error Handling

- Custom exception hierarchy in `src/aituber/core/exceptions.py`
- Service-specific exceptions inherit from `AITuberError`
- Graceful degradation without system crashes
- Comprehensive error context in exceptions