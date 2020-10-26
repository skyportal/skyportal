/*
{# Projects extending Skyportal can modify various segments of the About page by
  writing their own About.jsx.template which extends BaseAbout.jsx.template and
  overwrites the Jinja template blocks they wish to customize. Here, we just
  render the base template as is. This way, just the specific parts that need to
  be customized/appended to can be overwritten without having to overwrite the
  entire About.jsx component.

  Note that the base template uses comments to comment out Jinja-specific syntax
  like the block declarations in order to make the template double as a valid
  JSX file. Thus, further care should be taken when extending the template in
  order to keep those comment characters from commenting out the blocks you
  choose to overwrite. For example, you should place "*\/}" (without the escape
  backslash) after {% block %} declarations within the JSX component render()
  segment, and "{/*" immediately before the {% endblock %} declarations within
  the render().

  See https://jinja.palletsprojects.com/en/2.11.x/templates/#template-inheritance
  for documentation on usage of Jinja templates.
#}
*/

// {/* {% block imports -%} */}
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
import dayjs from "dayjs";

// {% endblock -%}

const useStyles = makeStyles((theme) => ({
  // {% block styles %}
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
    color: theme.palette.info.dark,
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
    color: `${theme.palette.secondary.dark} !important`,
  },
  gitlogPR: {
    color: theme.palette.primary.dark,
  },
  // {% endblock -%}
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
  // {% block componentConsts -%}
  const classes = useStyles();
  const version = useSelector((state) => state.sysInfo.version);
  const cosmology = useSelector((state) => state.sysInfo.cosmology);
  const cosmoref = useSelector((state) => state.sysInfo.cosmoref);
  const gitlog = useSelector((state) => state.sysInfo.gitlog);
  // {% endblock -%}

  // {% block configVariables -%}
  // Replace these with Jinja double-brace injection when extending
  const appTitle = "SkyPortal";
  // {% endblock -%}

  return (
    <Paper className={classes.root}>
      {/* {% block header -%} */}
      <Typography variant="h5">
        This is {appTitle}&nbsp;
        <code>v{version}</code>.
      </Typography>
      {/* {% endblock -%} */}
      {/* {% block projectIntro -%} */}
      <Typography variant="body1">
        The project homepage is at&nbsp;
        <a href="https://skyportal.io">https://skyportal.io</a>
      </Typography>
      {/* {% endblock -%} */}
      {/* {% block documentation -%} */}
      <Typography variant="body1">
        Documentation lives at&nbsp;
        <a href="https://skyportal.io">https://skyportal.io/docs/</a>
      </Typography>
      <Typography variant="body1">
        You may also interact with {appTitle} through its API. Generate a token
        from your&nbsp;
        <Link to="/profile">profile</Link>&nbsp; page, then refer to the&nbsp;
        <a href="https://skyportal.io/docs/api.html">API documentation</a>.
      </Typography>
      {/* {% endblock -%} */}
      {/* {% block githubIssues -%} */}
      <Typography variant="body1">
        Please file issues on our GitHub page at&nbsp;
        <a href="https://github.com/skyportal/skyportal">
          https://github.com/skyportal/skyportal
        </a>
      </Typography>
      {/* {% endblock -%} */}
      {/* {% block citation -%} */}
      <div>
        If you found SkyPortal useful, please consider citing our work:
        {/* {% raw -%} */}
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
          {/* {%- endraw -%} */}
          Stéfan J. van der Walt, Arien Crellin-Quick, Joshua S. Bloom,{" "}
          <em>SkyPortal: An Astronomical Data Platform.</em> Journal of Open
          Source Software, 4(37) 1247, May 2019.{" "}
          <a href="https://doi.org/10.21105/joss.01247">
            https://doi.org/10.21105/joss.01247
          </a>
          .
        </BibLink>
      </div>
      {/* {% endblock -%} */}
      {/* {% block acknowledgements -%} */}
      {/* {% endblock -%} */}
      {/* {% block gitlog -%} */}
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
      {/* {% endblock -%} */}
      {/* {% block cosmology -%} */}
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
      {/* {% endblock -%} */}
    </Paper>
  );
};

export default About;
