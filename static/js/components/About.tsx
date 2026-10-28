import { makeStyles } from "tss-react/mui";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import {
  AboutCitations,
  AboutFunding,
  AboutInstances,
  AboutIntro,
  AboutTeam,
} from "./templates/AboutPlugins";
import { AboutCard, PeopleGrid, Person } from "./about/AboutSections";
import UserAvatar from "./user/UserAvatar";
import { managerName } from "./deployment/InstanceManagers";
import { useGetConfigQuery } from "../ducks/config";
import { useGetInstanceManagersQuery } from "../ducks/instanceManagers";

const useStyles = makeStyles()(() => ({
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
  const cosmologyParams = (useGetConfigQuery().data as any)?.cosmologyParams;
  const cosmoref = (useGetConfigQuery().data as any)?.cosmoref;
  const { data: managers = [] } = useGetInstanceManagersQuery();

  return (
    <Stack spacing={3}>
      <AboutIntro />
      <AboutInstances />
      {managers.length > 0 && (
        <AboutCard title="Managed by">
          <PeopleGrid>
            {managers.map((manager) => (
              <Person
                key={manager.user_id}
                name={managerName(manager)}
                detail={manager.affiliations?.join(", ")}
                avatar={
                  <UserAvatar
                    size={80}
                    noTooltip
                    username={manager.username ?? ""}
                    firstName={manager.first_name ?? null}
                    lastName={manager.last_name ?? null}
                    gravatarUrl={manager.gravatar_url}
                    userId={manager.user_id}
                  />
                }
              />
            ))}
          </PeopleGrid>
        </AboutCard>
      )}
      <AboutTeam />
      <AboutCitations />
      <AboutCard title="Cosmology">
        <Typography variant="body1" component="div">
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
        </Typography>
      </AboutCard>
      <AboutFunding />
    </Stack>
  );
};

export default About;
