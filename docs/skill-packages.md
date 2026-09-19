# Capability packages

Open **Conversation options → Manage** beside the skill selector. Under
**Capability packages**, install Workspace inspector, Git reviewer, or Memory
recall. Review the listed tool access, click **Enable**, then select the package
for an agent conversation. Existing instruction-based workflows remain available.

Packages are local, versioned JSON manifests. They compose Alice's registered
native tools with focused instructions and an enforced tool allowlist. They do
not execute imported Python/JavaScript, install dependencies, or provide a
third-party plugin runtime. New native tool implementations still require a code
change and review in Alice's tool registry.

Example manifest, also suitable for the **Import or export a package** editor:

```json
{
  "schema_version": 1,
  "id": "project-reader",
  "name": "Project reader",
  "version": "1.0.0",
  "description": "Explain the current project from its source files.",
  "instructions": "Read relevant files before answering. Cite paths and never invent findings.",
  "tools": ["workspace_list", "workspace_read", "workspace_search"],
  "read_only": true,
  "requires": []
}
```

Imports and updates start disabled, even when replacing an enabled package.
Export copies the portable manifest into the editor without the local enable
state. Invalid fields, malformed IDs, or collisions with an existing workflow
are rejected. Unknown tools and missing requirements appear as health issues
and prevent enabling. Requirements currently support `git` and `docker`; these
checks establish that the executable is on PATH, not that a repository or Docker
daemon is healthy. Use the `sandbox_status` tool to check Docker availability.

The authenticated `/api/skill-packages` endpoint returns the installed packages,
starter templates, and native tool schemas. POST imports a manifest. PATCH
`/api/skill-packages/{id}` with `{"enabled": true}` enables it; DELETE removes it.
GET `/api/skill-packages/{id}/manifest` exports it. State persists atomically in
`ALICE_HOME/skill-packages.json`. A corrupt catalog is reported and cannot be
overwritten through these controls until repaired.

Tool restrictions apply to native tool calling and the JSON compatibility
protocol. Calls are checked again after an approval wait. Disabling, changing,
or removing a package prevents subsequent tool actions in that run; it does not
undo an action already executing. Stop the run to cancel ongoing work.
Read-only packages cannot write files, launch processes, delete memories, or
submit memory proposals. Write and process tools retain their normal individual
approval prompts even in an enabled package.

These are tool permissions, not a separate identity or data sandbox: existing
conversation context and approved personal memory still reach the model. Explicit
user “remember/recall/forget” commands retain their existing local behavior.
Legacy instruction presets keep their previous tool access. Select a capability
package to apply its narrower allowlist.

Restart Alice to load the upgrade. Rebuild packaged EXEs to include updated
Python modules and web assets. This release does not add semantic memory,
scheduled routines, or general desktop/browser control.
