import React from 'react';
import { useSelector } from 'react-redux';
import makeStyles from '@mui/styles/makeStyles';
import Grid from '@mui/material/Grid';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { useProfileGlobal } from './utils/useProfileGlobal';
import { getMockLLMVerdict } from './utils/mockProfiles';
import FeedbackButtons from './FeedbackButtons';

const useStyles = makeStyles((theme) => ({
  flexColumn: {
    display: 'flex',
    flexDirection: 'column',
    width: '100%',
  },
  accordionHeading: {
    fontSize: '1.25rem',
    fontWeight: theme.typography.fontWeightRegular,
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem'
  },
  content: {
    padding: '1rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  reasoningBox: {
    backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
    padding: '1rem',
    borderRadius: '4px',
    borderLeft: `4px solid ${theme.palette.info.main}`,
    fontStyle: 'italic',
  },
  headerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  }
}));

const LLMAccordion = ({ sourceId, gridStyle, orderClass }) => {
  const classes = useStyles();
  const { profileKey, profileData } = useProfileGlobal();
  const verdict = getMockLLMVerdict(sourceId, profileKey);

  return (
    <Grid item xs={12} lg={6} order={orderClass} style={gridStyle}>
      <Accordion defaultExpanded disableGutters className={classes.flexColumn}>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          id="llm-verdict-header"
        >
          <Typography className={classes.accordionHeading}>
            <SmartToyIcon color="primary" /> AI Triage Review ({profileData.name})
          </Typography>
        </AccordionSummary>
        <AccordionDetails className={classes.content}>
          <Box className={classes.headerRow}>
            <Typography variant="subtitle1" fontWeight="bold">
              Verdict: 
              <Chip 
                size="small" 
                label={verdict.verdict.toUpperCase()} 
                color={verdict.verdict === 'interesting' ? 'secondary' : 'default'}
                style={{ marginLeft: '0.5rem', fontWeight: 'bold' }}
              />
            </Typography>
            {verdict.suggested_class && (
              <Chip size="small" variant="outlined" label={`Suggested: ${verdict.suggested_class}`} />
            )}
          </Box>
          <Box className={classes.reasoningBox}>
            <Typography variant="body2">{verdict.reasoning}</Typography>
          </Box>
          <FeedbackButtons sourceId={sourceId} />
        </AccordionDetails>
      </Accordion>
    </Grid>
  );
};

export default LLMAccordion;
