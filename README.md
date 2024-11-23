# Agent-enhanced ACR

## Installation
- see environment-agent.yml
- TODO: actually check if it works (might be outdated)

## Notes on modifications from ACRv1
- agent architectures in `cog_arch/`
- uses `cognitive_base`, a collection of agent primitives. public version [here](https://github.com/nicholaschenai/cognitive_base_public) in case i commit with private/dev branch
- modded the internals (esp LM calls) with langchain so I can use caching and other tools
- various areas modded in `app/` to insert agent: `main.py`, `inference.py`, especially the patch writing and context collection main loops

## experiments
Experiments, status, code notes here: [cog_arch/docs/README.md](cog_arch/docs/README.md)
