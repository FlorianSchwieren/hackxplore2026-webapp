# Partnership Network Graph Consumption Guide

This document explains how a frontend or another agent should consume the demo graph endpoint:

```http
GET https://hackxplore2026-webapp.onrender.com/api/v1/me/partnership-network
```

The endpoint is designed for a **display-only network visualization**. It returns a bounded graph of users, trees, and partnership edges centered on the current dev-auth user, **Taylor Team**.

In local/dev/prod demo mode, no auth header is required when `DEV_AUTH_DISABLED=true`.

---

## Mental Model

The response is a **bipartite graph**:

```text
User node  -- partnership edge -->  Tree node
```

There are no direct user-to-user edges. Users are connected **through trees** because multiple users can have active partnerships on the same tree.

The graph expands from Taylor Team like this:

```text
Taylor Team
  -> Taylor's trees
  -> co-partners on those trees
  -> co-partners' trees
  -> users on those trees
  -> those users' trees
  -> third-degree users
  -> third-degree users' trees
```

The endpoint is capped so the total returned entity count stays below 200 for demo rendering.

---

## Endpoint

```bash
curl "https://hackxplore2026-webapp.onrender.com/api/v1/me/partnership-network"
```

Optional query params:

| Param | Default | Range | Meaning |
|---|---:|---:|---|
| `max_entities` | `200` | `50`–`200` | Hard cap for `users + trees + partnerships` |
| `max_users_per_depth` | `20` | `1`–`50` | Max newly discovered users per depth layer |

Example:

```bash
curl "https://hackxplore2026-webapp.onrender.com/api/v1/me/partnership-network?max_entities=180&max_users_per_depth=15"
```

---

## Top-Level Shape

```json
{
  "root_user_id": "7e33b42d-e8ff-5261-91fe-c2f0d8fc44c0",
  "max_depth": 3,
  "entity_count": 171,
  "truncated": false,
  "users": [],
  "trees": [],
  "partnerships": []
}
```

| Field | Type | Meaning |
|---|---|---|
| `root_user_id` | UUID string | Taylor Team / current user |
| `max_depth` | number | Currently `3` |
| `entity_count` | number | `users.length + trees.length + partnerships.length` |
| `truncated` | boolean | `true` if the API removed outer nodes to stay below `max_entities` |
| `users` | array | User nodes |
| `trees` | array | Tree nodes |
| `partnerships` | array | Edges between users and trees |

Current demo data is usually:

```text
users: 31
trees: 55
partnerships: 85
entity_count: 171
```

---

## `users[]`

Each user node:

```json
{
  "user_id": "0ca1bda0-f51b-5776-ab2c-751991d42658",
  "display_name": "Noel 24",
  "avatar_url": null,
  "depth": 3
}
```

| Field | Type | Meaning |
|---|---|---|
| `user_id` | UUID string | Stable user/profile id |
| `display_name` | string | Display name |
| `avatar_url` | string \| null | Optional avatar |
| `depth` | number | Graph distance layer from Taylor |

User depth:

| Depth | Meaning |
|---:|---|
| `0` | Taylor Team |
| `1` | Taylor's direct co-partners |
| `2` | Users connected through co-partners' trees |
| `3` | Users connected through second-degree users' trees |

---

## `trees[]`

Each tree node:

```json
{
  "tree_id": "06c1289a-7bd5-425c-9654-811defb1c8d6",
  "name": "Noble Willow Smith",
  "moisture_pct": 51.47,
  "health_state": "healthy",
  "health_state_app": "healthy",
  "depth": 3
}
```

| Field | Type | Meaning |
|---|---|---|
| `tree_id` | UUID string | Stable tree id |
| `name` | string | Funny display name |
| `moisture_pct` | number \| null | Current/mock current moisture percentage |
| `health_state` | string \| null | Backend health enum |
| `health_state_app` | string \| null | Flutter/mobile-friendly health enum |
| `depth` | number | First layer where this tree appears |

Tree depth:

| Depth | Meaning |
|---:|---|
| `0` | Taylor's own trees |
| `1` | Direct co-partners' trees |
| `2` | Second-degree users' trees |
| `3` | Third-degree users' trees |

### Health Fields

The API returns both health enums:

| Field | Values | Use |
|---|---|---|
| `health_state` | `thriving`, `healthy`, `thirsty`, `critical`, `overwatered` | Backend/dashboard fidelity |
| `health_state_app` | `healthy`, `warning`, `overmoisturized`, `dead` | Flutter/mobile enum |

Mapping:

| `health_state` | `health_state_app` |
|---|---|
| `thriving`, `healthy` | `healthy` |
| `thirsty` | `warning` |
| `overwatered` | `overmoisturized` |
| `critical` | `dead` |

If building a mobile UI, prefer `health_state_app`. If building a dashboard or debugging view, prefer `health_state`.

---

## `partnerships[]`

Each partnership is an edge connecting one user to one tree:

```json
{
  "user_id": "0ca1bda0-f51b-5776-ab2c-751991d42658",
  "tree_id": "06c1289a-7bd5-425c-9654-811defb1c8d6",
  "role": "owner",
  "depth": 3
}
```

| Field | Type | Meaning |
|---|---|---|
| `user_id` | UUID string | References `users[].user_id` |
| `tree_id` | UUID string | References `trees[].tree_id` |
| `role` | string | `owner`, `member`, or `caretaker` |
| `depth` | number | Max of the connected user/tree depths |

For the demo data, edges are mostly:

| Role | Meaning |
|---|---|
| `owner` | User owns/tends this tree |
| `member` | User is a co-partner on this tree |

---

## TypeScript Types

```ts
type HealthState =
  | 'thriving'
  | 'healthy'
  | 'thirsty'
  | 'critical'
  | 'overwatered';

type AppHealthState =
  | 'healthy'
  | 'warning'
  | 'overmoisturized'
  | 'dead';

type NetworkUser = {
  user_id: string;
  display_name: string;
  avatar_url: string | null;
  depth: number;
};

type NetworkTree = {
  tree_id: string;
  name: string;
  moisture_pct: number | null;
  health_state: HealthState | null;
  health_state_app: AppHealthState | null;
  depth: number;
};

type PartnershipEdge = {
  user_id: string;
  tree_id: string;
  role: 'owner' | 'member' | 'caretaker';
  depth: number;
};

type PartnershipNetworkResponse = {
  root_user_id: string;
  max_depth: number;
  entity_count: number;
  truncated: boolean;
  users: NetworkUser[];
  trees: NetworkTree[];
  partnerships: PartnershipEdge[];
};
```

---

## Recommended Frontend Consumption

Build lookup maps first:

```ts
const userById = new Map(data.users.map((user) => [user.user_id, user]));
const treeById = new Map(data.trees.map((tree) => [tree.tree_id, tree]));
```

Then resolve edges:

```ts
const graphEdges = data.partnerships.map((edge) => ({
  ...edge,
  user: userById.get(edge.user_id),
  tree: treeById.get(edge.tree_id),
}));
```

For rendering, treat users and trees as separate node types:

```ts
const nodes = [
  ...data.users.map((user) => ({
    id: `user:${user.user_id}`,
    type: 'user',
    label: user.display_name,
    depth: user.depth,
    data: user,
  })),
  ...data.trees.map((tree) => ({
    id: `tree:${tree.tree_id}`,
    type: 'tree',
    label: tree.name,
    depth: tree.depth,
    data: tree,
  })),
];

const edges = data.partnerships.map((partnership) => ({
  id: `${partnership.user_id}:${partnership.tree_id}:${partnership.role}`,
  source: `user:${partnership.user_id}`,
  target: `tree:${partnership.tree_id}`,
  label: partnership.role,
  depth: partnership.depth,
}));
```

---

## Display Guidance

Suggested visual encoding:

| Value | Suggested UI |
|---|---|
| User node | Circle/avatar |
| Tree node | Tree icon/card |
| `depth` | Ring distance, opacity, or color shade |
| `role=owner` | Solid edge |
| `role=member` | Dashed edge |
| `health_state_app=healthy` | Green |
| `health_state_app=warning` | Orange |
| `health_state_app=overmoisturized` | Blue/purple |
| `health_state_app=dead` | Red/gray |

Avoid nesting the graph by hand. The API is already normalized; render nodes + edges.

---

## Important Notes

1. This endpoint is **display-focused** and intentionally separate from `GET /me/co-partners`.
2. It returns active partnerships only:

```sql
active_to IS NULL OR active_to >= CURRENT_DATE
```

3. It is capped by `max_entities`; if `truncated=true`, outer-depth entities were removed.
4. Use `entity_count` as a quick sanity check before graph layout.
5. The demo seed is deterministic, so names and IDs should be stable across re-seeds.

---

## Minimal Fetch Example

```ts
async function fetchPartnershipNetwork(): Promise<PartnershipNetworkResponse> {
  const response = await fetch(
    'https://hackxplore2026-webapp.onrender.com/api/v1/me/partnership-network',
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch network: ${response.status}`);
  }

  return response.json();
}
```

---

## Quick Validation

```bash
curl -s "https://hackxplore2026-webapp.onrender.com/api/v1/me/partnership-network" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["entity_count"], d["max_depth"], d["truncated"])'
```

Expected current demo output:

```text
171 3 False
```

