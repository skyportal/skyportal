import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import MenuItem from "@material-ui/core/MenuItem";
import Typography from "@material-ui/core/Typography";
import Select from "@material-ui/core/Select";
import Slider from "@material-ui/core/Slider";
import InputLabel from "@material-ui/core/InputLabel";
import FormControl from "@material-ui/core/FormControl";
import Accordion from "@material-ui/core/Accordion";
import AccordionSummary from "@material-ui/core/AccordionSummary";
import AccordionDetails from "@material-ui/core/AccordionDetails";
import ExpandMoreIcon from "@material-ui/icons/ExpandMore";
import Button from "@material-ui/core/Button";
import { makeStyles, withStyles } from "@material-ui/core/styles";

import { showNotification } from "baselayer/components/Notifications";
import { getSortedClasses } from "./ShowClassification";
import * as Actions from "../ducks/source";

const useStyles = makeStyles(() => ({
  container: {
    padding: "1rem",
  },
  taxonomySelect: {
    minWidth: "10rem",
  },
  sliderContainer: {
    display: "flex",
    flexFlow: "row wrap",
    "& > div": {
      margin: "1rem 2rem",
    },
  },
  submitButton: {
    margin: "1rem 0",
  },
}));

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
export const allowedClasses = (hierarchy) => {
  if (!hierarchy) {
    return null;
  }

  const classPaths = [];
  addNodePaths(classPaths, hierarchy);

  const classes = classPaths.map((path) => ({
    class: path.pop(),
    context: path.reverse(),
  }));

  return classes;
};

const MultipleClassificationsForm = ({
  objId,
  taxonomyList,
  groupId,
  currentClassifications,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [selectedTaxonomy, setSelectedTaxonomy] = useState();
  const [submissionRequestInProcess, setSubmissionRequestInProcess] =
    useState(false);

  const latestTaxonomyList = taxonomyList.filter((t) => t.isLatest);

  const initialFormState = {};
  latestTaxonomyList.forEach((taxonomy) => {
    initialFormState[taxonomy.id] = {};
  });
  const sortedClassifications = getSortedClasses(currentClassifications);

  // For each existing taxonomy/classification, update initial sliders
  sortedClassifications.forEach((classifications) => {
    classifications.forEach((classification) => {
      initialFormState[classification.taxonomy_id][
        classification.classification
      ] = classification.probability;
    });
  });
  const [formState, setFormState] = useState(initialFormState);

  const getNode = (classification, path) => {
    // Get node from hierarchy
    let node;
    let hierarchy = selectedTaxonomy?.hierarchy.subclasses;
    const pathCopy = [...path];

    while (pathCopy.length > 0) {
      const ancestor = pathCopy.pop();
      node = hierarchy?.find((x) => x.class === ancestor);
      hierarchy = node?.subclasses;
    }
    node = hierarchy?.find((x) => x.class === classification);
    return node;
  };

  const sumChildren = (node, newFormState) => {
    // Sum the probabilities of the children
    const children = node?.subclasses;
    let sum = 0;
    children?.forEach((subclass) => {
      sum += newFormState[selectedTaxonomy.id][subclass.class] || 0;
    });

    return sum;
  };

  const updateChildren = (classification, newValue, newFormState) => {
    classification.subclasses?.forEach((subclass) => {
      newFormState[selectedTaxonomy.id][subclass.class] = Math.min(
        newValue,
        newFormState[selectedTaxonomy.id][subclass.class] || 0
      );
      updateChildren(subclass, newValue, newFormState);
    });
  };

  const handleChange = (newValue, classification, path) => {
    const newFormState = { ...formState };
    newFormState[selectedTaxonomy.id][classification] = newValue;

    // Update higher-level classification probabilities to be
    // the maximum between the current probability and the sum
    // of the subclasses' probabilities.
    path.forEach((ancestor, i) => {
      const probabilityOfSubclasses = Math.min(
        sumChildren(getNode(ancestor, path.slice(i + 1)), newFormState),
        1
      );
      newFormState[selectedTaxonomy.id][ancestor] = Math.max(
        probabilityOfSubclasses,
        newFormState[selectedTaxonomy.id][ancestor] || 0
      );
    });

    // Update subclasses' probabilities to be the minimum
    // between the current probability and the new value
    const node = getNode(classification, path);
    updateChildren(node, newValue, newFormState);
    setFormState(newFormState);
  };

  const renderSliders = (classifications, depth, path) =>
    classifications?.map((classification) => {
      const sliderBaseWidth = "10rem";
      const StyledSlider = withStyles({
        sliderDiv: {
          textAlign: "end",
        },
        slider: {
          width: `calc(${sliderBaseWidth} * (1 - .15 * ${depth}))`,
        },
        sliderLabel: {
          width: `calc(${sliderBaseWidth} * (1 - .15 * ${depth}))`,
          marginLeft: `calc(${sliderBaseWidth} * .15 * ${depth})`,
          textAlign: "left",
        },
      })(({ classes: styles }) => (
        <div className={styles.sliderDiv}>
          <Typography className={styles.sliderLabel} gutterBottom>
            {classification.class}
          </Typography>
          <Slider
            className={styles.slider}
            value={formState[selectedTaxonomy.id][classification.class] || 0}
            onChangeCommitted={(_, value) =>
              handleChange(value, classification.class, path)
            }
            id={classification.class}
            aria-labelledby={classification.class}
            valueLabelDisplay="auto"
            step={0.25}
            marks
            min={0}
            max={1.0}
          />
          {renderSliders(
            classification.subclasses,
            depth + 1,
            [classification.class].concat(path)
          )}
        </div>
      ));
      return <StyledSlider key={`${classification.class}`} />;
    });

  const handleSubmit = async () => {
    setSubmissionRequestInProcess(true);
    const results = [];

    Object.entries(formState).forEach(
      // Submit non-zero classifications for each taxonomy
      ([taxonomy, classifications]) => {
        Object.entries(classifications).forEach(
          async ([classification, probability]) => {
            if (probability > 0) {
              const data = {
                taxonomy_id: taxonomy,
                obj_id: objId,
                classification,
                probability,
                group_ids: [groupId],
              };
              const result = await dispatch(Actions.addClassification(data));
              results.push(result);
            }
          }
        );
      }
    );

    setSubmissionRequestInProcess(false);
    if (results.every((result) => result.status === "success")) {
      dispatch(showNotification("Classifications saved."));
    }
  };

  return (
    <div className={classes.container}>
      <Typography variant="h6">Edit Classifications</Typography>
      <FormControl className={classes.taxonomySelect}>
        <InputLabel id={`taxonomy-select-label-${objId}`}>
          Select Taxonomy
        </InputLabel>
        <Select
          labelId={`taxonomy-select-label-${objId}`}
          id={`taxonomy-select-${objId}`}
          value={selectedTaxonomy || ""}
          onChange={(event) => setSelectedTaxonomy(event.target.value)}
        >
          {latestTaxonomyList.map((taxonomy) => (
            <MenuItem key={taxonomy.name} value={taxonomy}>
              {taxonomy.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {selectedTaxonomy?.hierarchy?.subclasses?.map((category) => (
        <Accordion
          className={classes.classifications}
          key={`${category.class}`}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="classifications-content"
            id="classifications-header"
          >
            <Typography
              variant="subtitle1"
              className={classes.accordionHeading}
            >
              {category.class}
            </Typography>
          </AccordionSummary>
          <AccordionDetails className={classes.sliderContainer}>
            {renderSliders(category.subclasses, 0, [category.class])}
          </AccordionDetails>
        </Accordion>
      ))}
      <div className={classes.submitButton}>
        <Button
          variant="contained"
          color="primary"
          type="submit"
          name="submitClassificationsButton"
          disabled={submissionRequestInProcess}
          onClick={handleSubmit}
        >
          Submit classifications
        </Button>
      </div>
    </div>
  );
};

MultipleClassificationsForm.propTypes = {
  objId: PropTypes.string.isRequired,
  taxonomyList: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string,
      created_at: PropTypes.string,
      isLatest: PropTypes.bool,
      version: PropTypes.string,
    })
  ).isRequired,
  groupId: PropTypes.number.isRequired,
  currentClassifications: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
};

export default MultipleClassificationsForm;
