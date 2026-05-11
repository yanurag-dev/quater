---
layout: home

hero:
  text: Typed Python APIs for people and agents.
  tagline: Build one route surface for HTTP and MCP tools, with explicit auth and fast msgspec serialization.
  actions:
    - theme: brand
      text: Start Building
      link: /en/latest/quickstart
    - theme: alt
      text: Public API
      link: /en/latest/api

features:
  - title: One handler, two surfaces
    details: A route can stay a normal HTTP endpoint and, when you opt in, become an MCP tool without creating a second app path.
  - title: Auth stays visible
    details: HTTP routes use route-level auth. MCP has a transport auth boundary, then the same route auth inside tool calls.
  - title: Built around speed
    details: "Quater keeps the hot path small: Granian on RSGI, msgspec for JSON, and a native router underneath."
  - title: Docs by default
    details: OpenAPI, Swagger UI, and MCP tool docs are generated from the route metadata you already wrote.
---
