/*
 * Templater user script: vaultType(tp, typeName)
 *
 * Reads the governance schema (`00 Governance/Schemas/types.yml`) and returns a
 * note type's Status pick-list, home folder, and recommended (optional) props,
 * so templates and the `vault_governance` validator share ONE source of truth.
 *
 * Deliberately uses only `app` + string parsing — NO require("obsidian") — so it
 * loads and runs on desktop AND mobile (Android/iOS).
 *
 * Returns: { statuses: string[], folder: string, recommended: string[] }
 *   - folder: first `folder_globs` entry with the trailing glob stripped
 *     ("Human/03 Projects/**" -> "Human/03 Projects"; "**" -> "" = no move).
 */
async function vaultType(tp, typeName) {
  const result = { statuses: [], folder: "", recommended: [] };
  try {
    const raw = await app.vault.adapter.read("00 Governance/Schemas/types.yml");
    const start = raw.indexOf("\n  " + typeName + ":");
    if (start < 0) {
      console.error("vaultType: no type '" + typeName + "' in types.yml");
      return result;
    }
    // Isolate this type's block: from its key to the next top-level type key.
    const rest = raw.slice(start + 1);
    const next = rest.search(/\n  [A-Z]/);
    const block = next > 0 ? rest.slice(0, next) : rest;

    const list = (re) => {
      const m = block.match(re);
      return m ? m[1].split(",").map((s) => s.trim()).filter(Boolean) : [];
    };
    result.statuses = list(/statuses:\s*\[([^\]]*)\]/);
    result.recommended = list(/recommended:\s*\[([^\]]*)\]/);

    const fm = block.match(/folder_globs:\s*\[\s*"?([^"\],]+)"?/);
    if (fm) result.folder = fm[1].trim().replace(/\/?\*+.*$/, "").replace(/\/+$/, "");
  } catch (e) {
    console.error("vaultType:", e);
  }
  return result;
}

module.exports = vaultType;
