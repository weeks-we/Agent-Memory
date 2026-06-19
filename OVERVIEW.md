# Agent Memory Survey Paper List

This is the companion paper list repository for the survey:
**"From Historical Signals to Action Utility: A Survey of Memory Mechanisms for LLM-based Agents"**

## Project Structure

```
agent-memory-survey-paper-list/
├── README.md              # Main paper list organized by survey taxonomy
├── LICENSE                # MIT License
├── .gitignore             # Git ignore rules
├── generate_readme.py     # Script to regenerate README from .bib file
├── assets/                # Figures and assets directory
└── references.bib         # (referenced from source, not included here)
```

## Taxonomy

This survey organizes agent memory through a unified chain:

```
Historical Signals → Memory Objects → Memory Representations → Memory Operations → Control Policies → Action Utility
```

### Six Major Categories:
1. **Memory Objects** - What should agents remember?
2. **Memory Representations** - How are memories carried?
3. **Memory Operations** - The lifecycle of agent memory
4. **Control Policies** - Who decides memory operations?
5. **Memory Utility & Applications** - What does memory enable?
6. **Evaluation & Benchmarks** - How is memory evaluated?

## Usage

To regenerate the README from the bibliography file:

```bash
python generate_readme.py
```

## License

MIT License - see [LICENSE](LICENSE) for details.
