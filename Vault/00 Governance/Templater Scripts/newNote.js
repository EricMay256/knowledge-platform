/*
 * Templater user script: newNote(tp, typeName, opts) -> Promise<object>
 *
 * Shared scaffolding for every note-creation template, so each template is just
 * a Type + a body. Prompts for a title, picks a Status from the type's schema
 * lifecycle (auto when there's exactly one, a picker when there are several,
 * blank when none), offers the type's optional/recommended properties via
 * pickProps, and stamps CreatedAt in UTC.
 *
 * opts (all optional):
 *   titlePrompt : string    prompt label (default "<Type> title")
 *   folder      : string    override the schema home folder ("" = no move)
 *   recommended : string[]  override the optional props offered ([] to skip)
 *
 * Returns { type, title, status, created, extraProps, folder }.
 */
async function newNote(tp, typeName, opts) {
  opts = opts || {};

  const meta = (tp.user && typeof tp.user.vaultType === "function")
    ? await tp.user.vaultType(tp, typeName)
    : { statuses: [], folder: "", recommended: [] };

  // Title — prompt only when the file is still an unnamed draft.
  let title = tp.file.title;
  if (!title || title.startsWith("Untitled")) {
    title = (await tp.system.prompt(opts.titlePrompt || (typeName + " title"))) || tp.file.title;
  }

  // Status — auto for a single lifecycle value, pick for several, blank for none.
  let status = "";
  if (meta.statuses.length === 1) {
    status = meta.statuses[0];
  } else if (meta.statuses.length > 1) {
    status = (await tp.system.suggester(
      meta.statuses, meta.statuses, false, "Status (Esc to leave blank)")) || "";
  }

  // Optional properties.
  const recommended = opts.recommended !== undefined ? opts.recommended : meta.recommended;
  let extraProps = "";
  if (typeof tp.user.pickProps === "function" && recommended.length) {
    const chosen = await tp.user.pickProps(tp, recommended);
    extraProps = chosen.map((k) => k + ":\n").join("");
  }

  const created = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
  const folder = opts.folder !== undefined ? opts.folder : meta.folder;
  return { type: typeName, title, status, created, extraProps, folder };
}

module.exports = newNote;
