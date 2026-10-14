function highlightText(element, searchValue) {
  const text = element.textContent;
  if (!searchValue) {
    element.textContent = text;
    return;
  }
  const escaped = searchValue.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));
  element.replaceChildren(
    ...parts.map((part, index) => {
      if (index % 2 === 0) return part;
      const mark = document.createElement("mark");
      mark.textContent = part;
      return mark;
    }),
  );
}

// Filter releases based on the search bar value
function filterReleases() {
  const searchValue = document
    .getElementById("search-bar")
    .value.trim()
    .toLowerCase();

  const releases = document.getElementsByClassName("release");
  const includeDescription =
    document.getElementById("includeDescription").checked;

  Array.from(releases).forEach((release) => {
    const releaseName = release.getElementsByClassName("releaseName")[0];
    const releaseDescription =
      release.getElementsByClassName("releaseDescription")[0];

    if (searchValue === "") {
      release.style.display = "";
      highlightText(releaseName, "");
      highlightText(releaseDescription, "");
      return;
    }

    if (
      releaseName.textContent.toLowerCase().includes(searchValue) ||
      (includeDescription &&
        releaseDescription.textContent.toLowerCase().includes(searchValue))
    ) {
      highlightText(releaseName, searchValue);
      highlightText(releaseDescription, includeDescription ? searchValue : "");
      release.style.display = "";
    } else {
      release.style.display = "none";
    }
  });
}
