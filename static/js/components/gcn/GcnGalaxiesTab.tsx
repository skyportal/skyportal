import { useState } from "react";

import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import Button from "../Button";
import GalaxyTable from "../galaxy/GalaxyTable";

/** The galaxy query's own parameters.
 *
 * Galaxies are static, so the event's time range and everything about
 * detections is beside the point here: the query is purely spatial, against
 * the localization. Only what the galaxy catalog endpoint actually reads is
 * offered.
 */
const galaxiesFormSchema = (catalogs: any[]) => ({
  type: "object",
  properties: {
    catalog_name: {
      type: "string",
      title: "Galaxy catalog",
      enum: catalogs.map((catalog) => catalog?.catalog_name),
      default: catalogs[0]?.catalog_name,
    },
    localizationCumprob: {
      type: "number",
      title: "Localization cumulative probability",
      default: 0.95,
    },
    maxDistance: {
      type: "number",
      title: "Maximum distance [Mpc]",
    },
  },
  required: [
    "localizationCumprob",
    ...(catalogs.length > 0 ? ["catalog_name"] : []),
  ],
});

const uiSchema = {
  "ui:grid": [{ catalog_name: 6, localizationCumprob: 3, maxDistance: 3 }],
};

interface GcnGalaxiesTabProps {
  dateobs: string;
  localizationName?: string | null;
  galaxyCatalogs: any[];
  galaxies?: any;
  isFetching?: boolean;
  /** Whether a query has been run. Without it there is no way to tell "not
   * asked yet" from "asked and got nothing", and the tab reported that it was
   * fetching in both cases. */
  hasRun?: boolean;
  onSearch: (args: { dateobs: string; filterParams: any }) => void;
}

const GcnGalaxiesTab = ({
  dateobs,
  localizationName,
  galaxyCatalogs,
  galaxies: data,
  isFetching,
  hasRun,
  onSearch,
}: GcnGalaxiesTabProps) => {
  const [formData, setFormData] = useState<Record<string, any>>({
    catalog_name: galaxyCatalogs[0]?.catalog_name,
    localizationCumprob: 0.95,
  });

  const handleSubmit = ({ formData: submitted }: any) => {
    onSearch({
      dateobs,
      filterParams: { ...submitted, localizationName, numPerPage: 100 },
    });
  };

  return (
    <div>
      <Grid container spacing={1} sx={{ mb: "1rem" }}>
        <Grid size={{ sm: 12 }}>
          <div data-testid="gcn-galaxies-form">
            <Form
              schema={galaxiesFormSchema(galaxyCatalogs) as any}
              formData={formData}
              onChange={((e: any) => setFormData(e.formData)) as any}
              uiSchema={uiSchema as any}
              validator={validator}
              onSubmit={handleSubmit as any}
              disabled={!!isFetching}
            >
              <Button primary type="submit" async loading={!!isFetching}>
                Find galaxies
              </Button>
            </Form>
          </div>
        </Grid>
      </Grid>

      {!hasRun && (
        <Typography variant="body1">
          Run the query to list galaxies inside this localization.
        </Typography>
      )}
      {hasRun && isFetching && (
        <Typography variant="h5">Fetching galaxies...</Typography>
      )}
      {hasRun && !isFetching && data?.galaxies?.length === 0 && (
        <Typography variant="h5">None</Typography>
      )}
      {hasRun && !isFetching && data?.galaxies?.length > 0 && (
        <GalaxyTable
          galaxies={data.galaxies}
          totalMatches={data.totalMatches}
          serverSide={false}
          {...({ showTitle: true } as any)}
        />
      )}
    </div>
  );
};

export default GcnGalaxiesTab;
