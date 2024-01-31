import React from "react";
import { useSelector } from "react-redux";

import makeStyles from "@mui/styles/makeStyles";
import Avatar from "@mui/material/Avatar";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";

import AboutPlugins from "./AboutPlugins";

const useStyles = makeStyles(() => ({
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
  hidden: {
    display: "none",
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

const About = () => {
  const classes = useStyles();
  const cosmology = useSelector((state) => state.sysInfo.cosmology);
  const cosmoref = useSelector((state) => state.sysInfo.cosmoref);

  const developers = [
    {
      name: "Sarah Antier",
      src: "/static/images/developers/antier.jpeg",
    },
    {
      name: "Joshua Bloom",
      src: "/static/images/developers/bloom.jpeg",
    },
    {
      name: "Michael Coughlin",
      src: "/static/images/developers/coughlin.jpg",
    },
    {
      name: "Matthew Graham",
      src: "/static/images/developers/graham.jpg",
    },
    {
      name: "Theophile Jegou du Laz",
      src: "/static/images/developers/laz.jpeg",
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
      name: "Leo Singer",
      src: "/static/images/developers/singer.jpg",
    },
    {
      name: "Stéfan van der Walt",
      src: "/static/images/developers/vanderwalt.jpg",
    },
  ];

  const alumni = [
    {
      name: "Arien Crellin-Quick",
      src: "/static/images/developers/crellinquick.jpg",
    },
    {
      name: "Thomas Culino",
      src: "/static/images/developers/culino.jpg",
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
      name: "Jada Lilleboe",
      src: "/static/images/developers/lilleboe.jpg",
    },
    {
      name: "Kyung Min Shin",
      src: "/static/images/developers/shin.jpg",
    },
  ];

  return (
    <Paper className={classes.root}>
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
      <Typography variant="body1">and our alumni:</Typography>
      <div>
        <Grid container spacing={2}>
          {alumni.map((dev) => (
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
      <div>
        <AboutPlugins />
      </div>
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
