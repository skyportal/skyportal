export const capitalize = (s) =>
  s && s.length > 0 ? s[0].toUpperCase() + s.slice(1) : "";

/**
 * Return a label for a user formatted as:
 *  - "First_name Last_name" if available, otherwise "username"
 *  - Username is appended as " (username)" if alwaysShowUsername = true
 *  - Affiliations are appended as " (Aff1, Aff2)" if showAffiliations = true
 *  - Email is appended as " (email)" if showEmail = true
 *  - Bots are displayed by their username only
 *
 * Examples:
 *  userLabel(user) => "First_name Last_name"
 *  userLabel(user, true, true, true) => "First_name Last_name (username) (email) (Aff1, Aff2)"
 */
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
