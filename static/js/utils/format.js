export const capitalize = (s) =>
  s && s.length > 0 ? s[0].toUpperCase() + s.slice(1) : "";

export const userLabel = (
  user,
  alwaysShowUsername = false,
  showAffiliations = false,
  showEmail = false,
) => {
  if (!user) return "...";

  const { username, first_name, last_name, affiliations = [], is_bot } = user;
  if (is_bot) return username;

  let affiliationsLabel = "";
  if (showAffiliations && affiliations.length) {
    const formattedAffiliations = affiliations
      .filter(Boolean)
      .map(capitalize)
      .sort();

    affiliationsLabel = formattedAffiliations.length
      ? ` (${formattedAffiliations.join(", ")})`
      : "";
  }

  let usernameLabel = alwaysShowUsername ? ` (${username})` : "";
  let emailLabel =
    showEmail && user.contact_email ? ` (${user.contact_email})` : "";

  if (!first_name || !last_name)
    return `${username}${emailLabel}${affiliationsLabel}`;
  return `${capitalize(first_name)} ${capitalize(
    last_name,
  )}${usernameLabel}${emailLabel}${affiliationsLabel}`;
};
