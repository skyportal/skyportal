import React, { useState } from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

import { makeStyles } from "@material-ui/core/styles";
import Card from "@material-ui/core/Card";
import CardContent from "@material-ui/core/CardContent";
import CardActions from "@material-ui/core/CardActions";
import Button from "@material-ui/core/Button";
import Typography from "@material-ui/core/Typography";
import Box from "@material-ui/core/Box";
import Paper from "@material-ui/core/Paper";

import clsx from "clsx";

const useStyles = makeStyles((theme) => ({
  root: {
    display: "inline-block",
    paddingLeft: "1em",
    paddingRight: "1em",
    maxWidth: "100rem",
    fontSize: "1rem",
  },
  bibcard: {
    marginTop: "1rem",
  },
  bibtex: {
    marginTop: "2rem",
    marginBottom: 0,
    color: theme.palette.info.dark,
  },
  hidden: {
    display: "none",
  },
  gitlogList: {
    fontFamily: "monospace",
  },
  gitlogSHA: {
    color: `${theme.palette.secondary.dark} !important`,
  },
  gitlogPR: {
    color: theme.palette.primary.dark,
  },
}));

const BibLink = ({ bibtex, children }) => {
  const classes = useStyles();
  const [folded, setFolded] = useState(true);

  return (
    <Card className={classes.bibcard}>
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
    <Box className={classes.root}>
      <h2>
        This is SkyPortal&nbsp;
        <code>v{version}</code>.
      </h2>
      <p>
        The project homepage is at&nbsp;
        <a href="https://skyportal.io">https://skyportal.io</a>
      </p>
      <p>
        Documentation lives at&nbsp;
        <a href="https://skyportal.io">https://skyportal.io/docs/</a>
      </p>
      <p>
        You may also interact with SkyPortal through its API. Generate a token
        from your&nbsp;
        <Link to="/profile">profile</Link>&nbsp; page, then refer to the&nbsp;
        <a href="https://skyportal.io/docs/api.html">API documentation</a>.
      </p>
      <p>
        Please file issues on our GitHub page at&nbsp;
        <a href="https://github.com/skyportal/skyportal">
          https://github.com/skyportal/skyportal
        </a>
      </p>
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
          <h2>Recent Changelog</h2>
          <Paper mt={1}>
            <Box p={1}>
              <ul className={classes.gitlogList}>
                {gitlog.map(
                  ({ time, sha, pr_desc, pr_nr, pr_url, commit_url }) => (
                    <li key={sha}>
                      [{time}
                      <a className={classes.gitlogSHA} href={commit_url}>
                        &nbsp;{sha}
                      </a>
                      ] {pr_desc}
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
              <div>
                See all the pull requests at{" "}
                <a href="https://github.com/skyportal/skyportal/pulls">
                  https://github.com/skyportal/skyportal/pulls
                </a>
              </div>
            </Box>
          </Paper>
        </>
      )}
      <h2>Cosmology</h2>
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
            <br />
            If you&apos;d like to change the cosmology, please do so in the{" "}
            <code>config.yaml</code> under <code>misc.cosmology</code>.
          </>
        )}
      </span>
    </Box>
  );
};

export default About;
