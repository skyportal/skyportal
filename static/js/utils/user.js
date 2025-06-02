export const userLabelWithAffiliations = (user) => {
  if (!user) return "loading...";

  const { username, first_name, last_name, affiliations = [], is_bot } = user;

  if (is_bot) return username;

  const formattedAffiliations = affiliations
    .filter(Boolean)
    .map((affiliation) =>
      affiliation.length > 1
        ? affiliation[0].toUpperCase() + affiliation.slice(1)
        : affiliation.toUpperCase(),
    )
    .sort();

  const affiliationsLabel =
    formattedAffiliations.length > 0
      ? ` (${formattedAffiliations.join(", ")})`
      : "";

  const capitalize = (s) =>
    s?.length > 1 ? s[0].toUpperCase() + s.slice(1) : s?.toUpperCase();

  if (!first_name || !last_name) return `${username}${affiliationsLabel}`;

  return `${capitalize(first_name)} ${capitalize(
    last_name,
  )}${affiliationsLabel}`;
};
