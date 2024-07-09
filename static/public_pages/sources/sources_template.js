// Filter sources based on the search bar value
function filterSources() {
  const searchValue = document
    .getElementById("search-bar")
    .value.trim()
    .toLowerCase();
  const sources = document.getElementsByClassName("sourceAndVersions");

  Array.from(sources).forEach((source) => {
    const sourceId = source.getElementsByClassName("sourceId")[0];
    if (sourceId.textContent.toLowerCase().includes(searchValue)) {
      // Mark the search value in the source name
      const re = new RegExp(searchValue, "gi");
      sourceId.innerHTML = sourceId.textContent.replace(
        re,
        (match) => `<mark>${match}</mark>`,
      );
      source.style.display = "";
    } else {
      source.style.display = "none";
    }
  });
}

// Display all the versions of a source
function displayVersions(sourceId) {
  const versions = document.getElementById(`versions-of-source-${sourceId}`);
  if (versions.style.display === "none") {
    versions.style.display = "block";
  } else {
    versions.style.display = "none";
  }
}
