A demo MCP server from the [Donkey Development Kit](https://docs.donkey-kit.dev)
demos. It answers one question: what is this SKU, what does it cost, and how
many are in stock?

## When to use it

Give it to an agent that handles product or order questions and needs a
catalogue lookup. Each call takes one SKU and returns the product's name, price
and stock level.

## How this asset is maintained

The asset is published by CI, not by hand. A pull request that changes the
server gets a dry run, which shows the plan in the job summary and sends
nothing. A merge publishes only what changed. The tool list and its parameters
below come from the server's code, so this page can't drift from what the
server declares.

The endpoint is a placeholder (`example.invalid`): this server is a demo and
isn't deployed.
