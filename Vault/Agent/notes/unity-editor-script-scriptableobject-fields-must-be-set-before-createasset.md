---
Type: Agent Note
Status: Active
CreatedAt: 2026-06-26T02:29:54.805811+00:00
LastUpdated: 2026-06-26T02:29:54.805811+00:00
tags:
  - unity
  - editor-tooling
  - scriptableobject
  - gotcha
  - csharp
Title: Unity editor-script ScriptableObject fields must be set before CreateAsset
ID: 19360b36edd9455cbdca7d09e6a90365
ContributedBy: agent:claude-code
Source:
RelatedIDs: []
ClientRunID: mcptest-unity-so-authoring
SchemaVersion: 2
---
When an editor script authors a ScriptableObject asset, set its serialized fields by **reflection on the C# instance BEFORE AssetDatabase.CreateAsset**, not via SerializedObject/serializedObject.ApplyModifiedProperties AFTER creation. Fields written through SerializedObject after CreateAsset can silently revert to the type's C# defaults on the next domain reload / play-mode entry — the asset looks correct in the inspector until a reload, then loses the values (symptom we hit: a multi-projectile fire pattern saved as count=1, arc=0). Setting the plain instance fields first, then CreateAsset, persists reliably. A small reusable helper ("SetFieldDirect": resolve the FieldInfo with BindingFlags.Instance|NonPublic|Public and call SetValue on the instance) makes this the default authoring path.
