/* eslint-disable no-unused-vars */

// Filter releases based on the search bar value
function filterReleases() {
  const searchValue = document
    .getElementById("search-bar")
    .value.trim()
    .toLowerCase();
  const releases = document.getElementsByClassName("release");

  Array.from(releases).forEach((release) => {
    const releaseName = release.getElementsByClassName("releaseName")[0];
    if (releaseName.textContent.toLowerCase().includes(searchValue)) {
      // Mark the search value in the source name
      const re = new RegExp(searchValue, "gi");
      releaseName.innerHTML = releaseName.textContent.replace(
        re,
        (match) => `<mark>${match}</mark>`,
      );
      release.style.display = "";
    } else {
      release.style.display = "none";
    }
  });
}
