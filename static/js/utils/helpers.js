import { useSelector } from "react-redux";

const getAnnotationValueString = (value) => {
  let valueString;
  const valueType = typeof value;
  switch (valueType) {
    case "number":
      valueString = value.toFixed(4);
      break;
    case "object":
      valueString = JSON.stringify(value, null, 2);
      break;
    default:
      valueString = value.toString();
  }
  return valueString;
};

// For each node in the hierarchy tree, add its full path from root
// to the nodePaths list
const addNodePaths = (nodePaths, hierarchy, prefix_path = []) => {
  const thisNodePath = [...prefix_path];

  if (
    hierarchy.class !== undefined &&
    hierarchy.class !== "Time-domain Source"
  ) {
    thisNodePath.push(hierarchy.class);
    nodePaths.push(thisNodePath);
  }

  hierarchy.subclasses?.forEach((item) => {
    if (typeof item === "object") {
      addNodePaths(nodePaths, item, thisNodePath);
    }
  });
};

// For each class in the hierarchy, return its name
// as well as the path from the root of hierarchy to that class
const allowedClasses = (hierarchy) => {
  const classPaths = [];
  addNodePaths(classPaths, hierarchy);

  return classPaths.map((path) => ({
    class: path.pop(),
    context: path.reverse(),
  }));
};

// Get unique classification names, in alphabetical order
function useClassifications() {
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const latestTaxonomyList = taxonomyList?.filter((t) => t.isLatest);
  let classifications = [];
  latestTaxonomyList?.forEach((taxonomy) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy)?.map(
      (option) => option.class,
    );
    classifications = classifications.concat(currentClasses);
  });
  return Array.from(new Set(classifications)).sort();
}

export { getAnnotationValueString, allowedClasses, useClassifications };
