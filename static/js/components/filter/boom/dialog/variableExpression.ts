// A stored arithmetic variable is "name = expression"; return just the
// expression so it can be loaded back into the editor when editing in place.
export const parseVariableExpression = (stored: string): string => {
  if (!stored) return "";
  const idx = stored.indexOf("=");
  return idx >= 0 ? stored.slice(idx + 1).trim() : stored.trim();
};
