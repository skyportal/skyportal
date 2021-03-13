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
import Avatar from "@material-ui/core/Avatar";
import Grid from "@material-ui/core/Grid";

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
    marginTop: "1rem",
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
  gitlogSHA: {
    color: `${theme.palette.error.main} !important`,
  },
  gitlogPR: {
    color: theme.palette.secondary.dark,
  },
  dev: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  devIcon: {
    width: "5rem",
    height: "5rem",
  },
  documentation: {
    float: "right",
    maxWidth: "20rem",
    padding: "0 1rem",
    margin: "1rem",
  },
  header: {
    display: "inline-block",
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

  const developers = [
    {
      name: "Joshua Bloom",
      src: "/static/images/developers/bloom.jpeg",
    },
    {
      name: "Michael Coughlin",
      src: "/static/images/developers/coughlin.jpg",
    },
    {
      name: "Arien Crellin-Quick",
      src: "/static/images/developers/crellinquick.jpg",
    },
    {
      name: "Dmitry Duev",
      src: "/static/images/developers/duev.jpg",
    },
    {
      name: "Daniel Goldstein",
      src: "/static/images/developers/goldstein.jpg",
    },
    {
      name: "Matthew Graham",
      src: "/static/images/developers/graham.jpg",
    },
    {
      name: "Mansi Kasliwal",
      src: "/static/images/developers/kasliwal.jpg",
    },
    {
      name: "Don Neill",
      src: "/static/images/developers/neill.jpg",
    },
    {
      name: "Guy Nir",
      src: "/static/images/developers/nir.jpg",
    },
    {
      name: "Kyung Min Shin",
      src: "/static/images/developers/shin.jpg",
    },
    {
      name: "Leo Singer",
      src: "/static/images/developers/singer.jpg",
    },
    {
      name: "Stéfan van der Walt",
      src: "/static/images/developers/vanderwalt.jpg",
    },
  ];
  return (
    <Paper className={classes.root}>
      <Typography className={classes.header} variant="h5">
        This is Fritz&nbsp;
        <code>v{version}</code>.
      </Typography>
      <Paper variant="outlined" className={classes.documentation}>
        <Typography variant="body1">
          Documentation for Fritz is available at{" "}
          <a href="https://docs.fritz.science/">https://docs.fritz.science/</a>.
        </Typography>
      </Paper>
      <Typography variant="body1">
        Fritz is an open source codebase that serves as a dynamic collaborative
        platform for time-domain astronomy. It is being jointly developed at
        Caltech and UC Berkeley.
      </Typography>
      <Typography variant="body1">Meet the core dev team:</Typography>
      <div>
        <Grid container spacing={2}>
          {developers.map((dev) => (
            <Grid item md={3} xs={4} key={dev.name}>
              <div className={classes.dev}>
                <Avatar
                  alt={dev.name}
                  src={dev.src}
                  className={classes.devIcon}
                />
                <Typography variant="body1">{dev.name}</Typography>
              </div>
            </Grid>
          ))}
        </Grid>
      </div>
      <Typography variant="body1">
        Fritz integrates and extends two projects,&nbsp;
        <a href="https://github.com/dmitryduev/kowalski">Kowalski</a>
        &nbsp;&&nbsp;
        <a href="https://skyportal.io">SkyPortal</a>, and has the functionality
        of an alert broker, a multi-survey data sink/archive, a marshal, and a
        target and observation/follow-up management tool.
      </Typography>
      <Typography variant="body1">
        You may also interact with Fritz through its API. Generate a token from
        your&nbsp;
        <Link to="/profile">profile</Link>&nbsp;page, then refer to the&nbsp;
        <a href="https://docs.fritz.science/api.html">API documentation</a>.
      </Typography>
      <Typography variant="body1">
        Please file issues on our GitHub page at&nbsp;
        <a href="https://github.com/fritz-marshal/fritz">
          https://github.com/fritz-marshal/fritz
        </a>
      </Typography>
      <div>
        If you found Fritz useful, please cite the following papers:
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
        <BibLink
          bibtex={`@article{duev2019real,
  title={Real-bogus classification for the Zwicky Transient Facility using deep learning},
  author={Duev, Dmitry A and Mahabal, Ashish and Masci, Frank J and Graham, Matthew J and Rusholme, Ben and Walters, Richard and Karmarkar, Ishani and Frederick, Sara and Kasliwal, Mansi M and Rebbapragada, Umaa and others},
  journal={Monthly Notices of the Royal Astronomical Society},
  volume={489},
  number={3},
  pages={3582--3590},
  year={2019},
  publisher={Oxford University Press}
  url={https://ui.adsabs.harvard.edu/abs/2019MNRAS.489.3582D/abstract}
}`}
        >
          Duev, Dmitry A., et al.,{" "}
          <em>
            Real-bogus classification for the Zwicky Transient Facility using
            deep learning.
          </em>{" "}
          Monthly Notices of the Royal Astronomical Society, 489(3) 3582-3590,
          2019.{" "}
          <a href="https://doi.org/10.1093/mnras/stz2357">
            https://doi.org/10.1093/mnras/stz2357
          </a>
          .
        </BibLink>
        <BibLink
          bibtex={`@article{Kasliwal_2019,
	doi = {10.1088/1538-3873/aafbc2},
	url = {https://doi.org/10.1088%2F1538-3873%2Faafbc2},
	year = 2019,
	month = {feb},
	publisher = {{IOP} Publishing},
	volume = {131},
	number = {997},
	pages = {038003},
	author = {M. M. Kasliwal and C. Cannella and A. Bagdasaryan and T. Hung and U. Feindt and L. P. Singer and M. Coughlin and C. Fremling and R. Walters and D. Duev and R. Itoh and R. M. Quimby},
	title = {The {GROWTH} Marshal: A Dynamic Science Portal for Time-domain Astronomy},
	journal = {Publications of the Astronomical Society of the Pacific},
}`}
        >
          Kasliwal, M., et al.,{" "}
          <em>
            The GROWTH marshal: a dynamic science portal for time-domain
            astronomy.
          </em>{" "}
          Publications of the Astronomical Society of the Pacific, 131(997)
          038003, Feb 2019.{" "}
          <a href="https://doi.org/10.1088%2F1538-3873%2Faafbc2">
            https://doi.org/10.1088%2F1538-3873%2Faafbc2
          </a>
          .
        </BibLink>
      </div>
      <Typography variant="body1">
        Fritz development is funded by the Moore Foundation, Heising Simons
        Foundation, National Science Foundation, NASA and the Packard
        Foundation.
      </Typography>
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
                  ({ time, sha, description, pr_nr, pr_url, commit_url }) => (
                    <li key={sha}>
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
            <br />
            If you&apos;d like to change the cosmology, please do so in the{" "}
            <code>config.yaml</code> under <code>misc.cosmology</code>.
          </>
        )}
      </span>
    </Paper>
  );
};

export default About;
