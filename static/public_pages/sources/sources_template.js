/* eslint-disable no-unused-vars */

// Filter sources based on the search bar value
function filterSources() {
  const searchValue = document
    .getElementById("search-bar")
    .value.trim()
    .toLowerCase();
  const sources = document.getElementsByClassName("sourceAndVersions");

  Array.from(sources).forEach((source) => {
    const sourceId = source.id.toLowerCase();
    if (sourceId.includes(searchValue)) {
      // Mark the search value in the source name
      const h2 = source.querySelector("h2");
      const re = new RegExp(searchValue, "gi");
      h2.innerHTML = source.id.replace(re, (match) => `<mark>${match}</mark>`);
      // Display the source versions
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
