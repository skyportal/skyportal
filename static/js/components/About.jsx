import React, { useState } from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

import makeStyles from "@mui/styles/makeStyles";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardActions from "@mui/material/CardActions";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";

import clsx from "clsx";
import dayjs from "dayjs";

const useStyles = makeStyles((theme) => ({
  root: {
    padding: "1rem 2rem 2rem 2rem",
    fontSize: "1rem",
    "& .MuiTypography-h5": {
      margin: "1rem 0 0.83rem 0",
      fontWeight: 600,
      wordBreak: "break-all",
    },
    "& .MuiTypography-body1": {
      margin: "1rem 0",
    },
  },
  bibcard: {
    marginTop: "5rem",
    "& .MuiTypography-body1": {
      margin: 0,
    },
  },
  bibtex: {
    marginTop: "2rem",
    marginBottom: 0,
    color: theme.palette.secondary.dark,
  },
  hidden: {
    display: "none",
  },
  gitlogPaper: {
    maxHeight: "30rem",
    overflow: "auto",
  },
  gitlogList: {
    fontFamily: "monospace",
  },
  gitlogName: {
    paddingRight: "0.25rem",
  },
  gitlogSHA: {
    color: `${theme.palette.error.main} !important`,
  },
  gitlogPR: {
    color: theme.palette.secondary.dark,
  },
}));

const BibLink = ({ bibtex, children }) => {
  const classes = useStyles();
  const [folded, setFolded] = useState(true);

  return (
    <Card className={classes.bibcard} variant="outlined">
      <CardContent>
        <Typography>{children}</Typography>
        <pre
          className={clsx(classes.bibtex, {
            [classes.hidden]: folded,
          })}
        >
          {bibtex}
        </pre>
      </CardContent>
      <CardActions>
        <Button size="small" onClick={() => setFolded(!folded)}>
          {folded ? "Show BiBTeX" : "Hide BiBTeX"}
        </Button>
      </CardActions>
    </Card>
  );
};
BibLink.propTypes = {
  bibtex: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
};

const About = () => {
  const classes = useStyles();
  const version = useSelector((state) => state.sysInfo.version);
  const cosmology = useSelector((state) => state.sysInfo.cosmology);
  const cosmoref = useSelector((state) => state.sysInfo.cosmoref);
  const gitlog = useSelector((state) => state.sysInfo.gitlog);
  return (
    <Paper className={classes.root}>
      <Typography variant="h5">
        This is SkyPortal&nbsp;
        <code>v{version}</code>.
      </Typography>
      <Typography variant="body1">
        The project homepage is at&nbsp;
        <a href="https://skyportal.io">https://skyportal.io</a>
      </Typography>
      <Typography variant="body1">
        Documentation lives at&nbsp;
        <a href="https://skyportal.io">https://skyportal.io/docs/</a>
      </Typography>
      <Typography variant="body1">
        You may also interact with SkyPortal through its API. Generate a token
        from your&nbsp;
        <Link to="/profile">profile</Link>&nbsp; page, then refer to the&nbsp;
        <a href="https://skyportal.io/docs/api.html">API documentation</a>.
      </Typography>
      <Typography variant="body1">
        Please file issues on our GitHub page at&nbsp;
        <a href="https://github.com/skyportal/skyportal">
          https://github.com/skyportal/skyportal
        </a>
      </Typography>
      <div>
        If you found SkyPortal useful, please consider citing our work:
        <BibLink
          bibtex={`@article{skyportal2019,
  author = {St\\'efan J. van der Walt and Arien Crellin-Quick and Joshua S. Bloom},
  title = {{SkyPortal}: An Astronomical Data Platform},
  journal = {Journal of Open Source Software},
  volume = {4},
  number = {37},
  page = {1247},
  year = {2019},
  month = {may},
  doi = {10.21105/joss.01247},
  url = {http://joss.theoj.org/papers/10.21105/joss.01247}
}`}
        >
          Stéfan J. van der Walt, Arien Crellin-Quick, Joshua S. Bloom,{" "}
          <em>SkyPortal: An Astronomical Data Platform.</em> Journal of Open
          Source Software, 4(37) 1247, May 2019.{" "}
          <a href="https://doi.org/10.21105/joss.01247">
            https://doi.org/10.21105/joss.01247
          </a>
          .
        </BibLink>
      </div>
      {gitlog && (
        <>
          <Typography variant="h5">Recent Changelog</Typography>
          <Paper mt={1} className={classes.gitlogPaper}>
            <Box p={1}>
              <div>
                See all pull requests at{" "}
                <a href="https://github.com/skyportal/skyportal/pulls?q=is%3Apr+">
                  https://github.com/skyportal/skyportal/pulls
                </a>
              </div>
              <ul className={classes.gitlogList}>
                {gitlog.map(
                  ({
                    name,
                    time,
                    sha,
                    description,
                    pr_nr,
                    pr_url,
                    commit_url,
                  }) => (
                    <li key={sha}>
                      {name && (
                        <span className={classes.gitlogName}>[{name}]</span>
                      )}
                      [{dayjs(time).format("YYYY-MM-DD")}
                      <a className={classes.gitlogSHA} href={commit_url}>
                        &nbsp;{sha}
                      </a>
                      ] {description}
                      {pr_nr && (
                        <a href={pr_url}>
                          &nbsp;(
                          <span className={classes.gitlogPR}>#{pr_nr}</span>)
                        </a>
                      )}
                    </li>
                  )
                )}
              </ul>
            </Box>
          </Paper>
        </>
      )}
      <Typography variant="h5">Cosmology</Typography>
      <span>
        The cosmology currently used here is an instance of{" "}
        <code>astropy.cosmology</code> with the parameters (see{" "}
        <a href="https://github.com/astropy/astropy/blob/master/astropy/cosmology/parameters.py">
          this link for parameters definitions): <br />
        </a>
        {cosmology && (
          <>
            <blockquote>{cosmology}</blockquote>
            <b>Reference</b>: {cosmoref}
          </>
        )}
      </span>
    </Paper>
  );
};

export default About;
