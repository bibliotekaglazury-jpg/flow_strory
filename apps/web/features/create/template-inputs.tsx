import type { useCreation } from "@/hooks/use-creation";
export function TemplateInputs({
  c,
  disabled,
}: {
  c: ReturnType<typeof useCreation>;
  disabled: boolean;
}) {
  const schema = c.selectedTemplate?.inputSchema;
  return (
    <div className="schema-fields">
      {Object.entries(schema?.properties ?? {}).map(([key, p]) => {
        const value = c.draft.normalizedInputs?.[key] ?? p.default ?? "";
        const change = (value: string | number | boolean | string[]) => {
          const inputs = { ...c.draft.normalizedInputs };
          if (value === "" && p.mediaType) delete inputs[key];
          else inputs[key] = value;
          c.update({ normalizedInputs: inputs });
        };
        return (
          <label key={key}>
            {p.title ?? key}
            {schema?.required?.includes(key) ? " *" : ""}
            {p.mediaType ? (
              <>
                <input
                  type="file"
                  disabled={disabled}
                  accept={
                    p.mediaType === "image"
                      ? "image/png,image/jpeg,image/webp"
                      : "video/mp4,video/webm,video/quicktime"
                  }
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) void c.uploadTemplateInput(f, key, p.mediaType!);
                  }}
                />
                {value && (
                  <small>
                    {c.assets.find((a) => a.id === value)?.fileName ??
                      "Image selected"}{" "}
                    <button
                      type="button"
                      onClick={() => change("")}
                      disabled={disabled}
                    >
                      Remove
                    </button>
                  </small>
                )}
              </>
            ) : p.enum ? (
              <select
                value={String(value)}
                onChange={(e) => change(e.target.value)}
                disabled={disabled}
              >
                {p.enum.map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            ) : p.type === "boolean" ? (
              <input
                type="checkbox"
                checked={Boolean(value)}
                onChange={(e) => change(e.target.checked)}
                disabled={disabled}
              />
            ) : (
              <input
                type={
                  p.type === "number" || p.type === "integer"
                    ? "number"
                    : "text"
                }
                value={Array.isArray(value) ? value.join(", ") : String(value)}
                min={p.minimum}
                max={p.maximum}
                maxLength={p.maxLength}
                required={schema?.required?.includes(key)}
                disabled={disabled}
                onChange={(e) =>
                  change(
                    p.type === "number" || p.type === "integer"
                      ? Number(e.target.value)
                      : p.type === "array"
                        ? e.target.value.split(",").map((v) => v.trim())
                        : e.target.value,
                  )
                }
              />
            )}{" "}
            {p.description && <small>{p.description}</small>}
          </label>
        );
      })}
    </div>
  );
}
