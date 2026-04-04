import React from 'react';
import makeStyles from '@mui/styles/makeStyles';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import ScienceIcon from '@mui/icons-material/Science';
import Box from '@mui/material/Box';
import Tooltip from '@mui/material/Tooltip';
import { useProfileGlobal } from './utils/useProfileGlobal';

const useStyles = makeStyles((theme) => ({
  formControl: {
    margin: theme.spacing(1),
    minWidth: 160,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: '8px',
  },
  select: {
    color: 'white',
    paddingTop: '6px',
    paddingBottom: '6px',
    '&:before': {
      borderColor: 'transparent',
    },
    '&:after': {
      borderColor: 'transparent',
    },
    '& .MuiSvgIcon-root': {
      color: 'white',
    }
  },
  menuItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  }
}));

const ProfileSelector = () => {
  const classes = useStyles();
  const { profileKey, setProfile, allProfiles, profileData } = useProfileGlobal();

  const handleChange = (e) => {
    setProfile(e.target.value);
  };

  return (
    <Tooltip title={`Current Profile: ${profileData.description}`}>
      <FormControl variant="standard" className={classes.formControl}>
        <Select
          value={profileKey}
          onChange={handleChange}
          className={classes.select}
          disableUnderline
          renderValue={(selected) => {
            const p = allProfiles.find(x => x.key === selected);
            return (
              <Box display="flex" alignItems="center" gap={1} pl={1}>
                <ScienceIcon fontSize="small" />
                <span>{p ? p.name : 'Unknown'}</span>
              </Box>
            );
          }}
        >
          {allProfiles.map((p) => (
            <MenuItem key={p.key} value={p.key} className={classes.menuItem}>
              <ScienceIcon fontSize="small" color="primary" />
              {p.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Tooltip>
  );
};

export default ProfileSelector;
