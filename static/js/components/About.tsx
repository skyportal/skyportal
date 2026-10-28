import { makeStyles } from "tss-react/mui";
import Avatar from "@mui/material/Avatar";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";

import AboutPlugins from "./templates/AboutPlugins";
import { useGetConfigQuery } from "../ducks/config";

interface TeamMember {
  name: string;
  image: string;
}

const useStyles = makeStyles()(() => ({
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
  cosmoTable: {
    borderCollapse: "collapse",
    margin: "0.5rem 0",
    "& td": {
      border: "1px solid",
      borderColor: "rgba(128,128,128,0.4)",
      padding: "2px 12px",
    },
    "& td:first-of-type": {
      fontWeight: 600,
    },
  },
}));

const About = () => {
  const { classes } = useStyles();
  // cosmology/cosmoref are served by `/api/config` and live in the `config`
  // slice; this previously read them from `sysInfo` (where they never existed),
  // so the block below never rendered. Sourced correctly now.
  const cosmologyParams = (useGetConfigQuery().data as any)?.cosmologyParams;
  const cosmoref = (useGetConfigQuery().data as any)?.cosmoref;

  const developers: TeamMember[] =
    (useGetConfigQuery().data as any)?.aboutDevelopers ?? [];
  const alumni: TeamMember[] =
    (useGetConfigQuery().data as any)?.aboutAlumni ?? [];

  const team = (people: TeamMember[]) => (
    <Grid container spacing={2}>
      {people.map((dev) => (
        <Grid size={{ md: 3, xs: 4 }} key={dev.name}>
          <div className={classes.dev}>
            <Avatar
              alt={dev.name}
              src={dev.image}
              className={classes.devIcon}
            />
            <Typography variant="body1">{dev.name}</Typography>
          </div>
        </Grid>
      ))}
    </Grid>
  );

  return (
    <Paper className={classes.root}>
      <Typography variant="body1">Meet the SkyPortal dev team:</Typography>
      {team(developers)}
      <Typography variant="body1">and our alumni:</Typography>
      {team(alumni)}
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
        {cosmologyParams && (
          <>
            <table className={classes.cosmoTable}>
              <tbody>
                {cosmologyParams.map(
                  (param: { name: string; value: string }) => (
                    <tr key={param.name}>
                      <td>{param.name}</td>
                      <td>{param.value}</td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
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
