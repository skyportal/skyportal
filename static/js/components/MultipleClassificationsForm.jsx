import React, { useState } from "react";
import { useSelector } from "react-redux";
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
import { makeStyles, withStyles } from "@material-ui/core/styles";

// import { showNotification } from "baselayer/components/Notifications";
// import * as Actions from "../ducks/source";

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

const MultipleClassificationsForm = ({ obj_id, taxonomyList }) => {
  const classes = useStyles();
  // const dispatch = useDispatch();
  const groups = useSelector((state) => state.groups.userAccessible);

  const [selectedTaxonomy, setSelectedTaxonomy] = useState();
  // const [submissionRequestInProcess, setSubmissionRequestInProcess] =
  //   useState(false);

  const [formState, setFormState] = useState({});

  const groupIDToName = {};
  groups.forEach((g) => {
    groupIDToName[g.id] = g.name;
  });

  const latestTaxonomyList = taxonomyList.filter((t) => t.isLatest);

  const handleChange = (newValue, classification) => {
    const newFormState = { ...formState };
    newFormState[classification] = newValue;
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
            value={formState[classification.class] || 0}
            onChangeCommitted={(_, value) =>
              handleChange(value, classification.class)
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

  // const handleSubmit = async ({ formData }) => {
  //   setSubmissionRequestInProcess(true);
  //   // Get the classification without the context
  //   const classification = formData.classification.split(" <> ")[0];
  //   const data = {
  //     taxonomy_id: parseInt(formData.taxonomy, 10),
  //     obj_id,
  //     classification,
  //     probability: formData.probability,
  //   };
  //   if (formData.groupIDs) {
  //     data.group_ids = formData.groupIDs.map((id) => parseInt(id, 10));
  //   }
  //   const result = await dispatch(Actions.addClassification(data));
  //   setSubmissionRequestInProcess(false);
  //   if (result.status === "success") {
  //     dispatch(showNotification("Classification saved"));
  //   }
  // };

  // const currentClasses = allowedClasses(selectedTaxonomy?.hierarchy)?.map(
  //   (option) =>
  //     `${option.class} <> ${
  //       option.context.length > 0 ? option.context.join(" « ") : ""
  //     }`
  // );

  return (
    <div className={classes.container}>
      <Typography variant="h6">Edit Classifications</Typography>
      <FormControl className={classes.taxonomySelect}>
        <InputLabel id={`taxonomy-select-label-${obj_id}`}>
          Select Taxonomy
        </InputLabel>
        <Select
          labelId={`taxonomy-select-label-${obj_id}`}
          id={`taxonomy-select-${obj_id}`}
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
            {renderSliders(category.subclasses, 0, [])}
          </AccordionDetails>
        </Accordion>
      ))}
    </div>
  );
};

MultipleClassificationsForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
  taxonomyList: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string,
      created_at: PropTypes.string,
      isLatest: PropTypes.bool,
      version: PropTypes.string,
    })
  ).isRequired,
};

export default MultipleClassificationsForm;
