/*
 * Templater user script: pickProps(tp, options) -> Promise<string[]>
 *
 * Lets the user choose which optional properties to add to a new note. Resolves
 * to the array of property names they selected.
 *
 * Adaptive so it works everywhere:
 *   - If Obsidian's Modal/Setting are reachable (require("obsidian") works, i.e.
 *     desktop) it shows a real checkbox/toggle modal.
 *   - Otherwise (mobile, or any build where window.require can't resolve
 *     "obsidian") it falls back to a native repeated tp.system.suggester picker,
 *     which needs no require at all.
 *
 * Templater loads user scripts with `require = u => window.require && window.require(u)`,
 * so require("obsidian") may return undefined or throw — hence the guarded probe.
 */
async function pickProps(tp, options) {
  if (!options || !options.length) return [];

  let Modal, Setting;
  try {
    const obs = require("obsidian");
    if (obs) ({ Modal, Setting } = obs);
  } catch (e) {
    // require unavailable / "obsidian" not resolvable — use the fallback below.
  }

  // --- Preferred: checkbox (toggle) modal -------------------------------------
  if (Modal && Setting) {
    return await new Promise((resolve) => {
      const modal = new Modal(app);
      modal.titleEl.setText("Optional properties");

      const chosen = new Set();
      for (const key of options) {
        new Setting(modal.contentEl)
          .setName(key)
          .addToggle((t) => t.onChange((v) => { v ? chosen.add(key) : chosen.delete(key); }));
      }

      let submitted = false;
      new Setting(modal.contentEl).addButton((b) =>
        b.setButtonText("Add selected").setCta().onClick(() => {
          submitted = true;
          modal.close();
          resolve([...chosen]);
        }));
      modal.onClose = () => { if (!submitted) resolve([...chosen]); };
      modal.open();
    });
  }

  // --- Fallback: native multi-select, no require -------------------------------
  const remaining = [...options];
  const chosen = [];
  while (remaining.length) {
    const labels = ["✓ Done", ...remaining.map((p) => "＋ " + p)];
    const values = [null, ...remaining];
    const pick = await tp.system.suggester(
      labels, values, false, "Add optional property (✓ Done to finish)");
    if (!pick) break; // Done or Esc
    chosen.push(pick);
    remaining.splice(remaining.indexOf(pick), 1);
  }
  return chosen;
}

module.exports = pickProps;
