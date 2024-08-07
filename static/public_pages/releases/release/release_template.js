// Display all the versions of a source
function displayVersions(sourceId) {
  const versions = document.getElementById(`versions-of-source-${sourceId}`);
  if (versions.style.display === "none") {
    versions.style.display = "block";
  } else {
    versions.style.display = "none";
  }
}
