import React from 'react';
import { useSelector } from 'react-redux';
import Grid from '@material-ui/core/Grid';
import SkyCam from './SkyCam';

const SkyCamPage = () => {

  const { telescopeList } = useSelector((state) => (state.telescopes));

  return (
    <Grid container spacing={3}>
      {
        telescopeList.map((scope) => (
          <Grid item>
            <SkyCam telescope={scope}/>
          </Grid>
        ))
      }
    </Grid>
  );
};


export default SkyCamPage;
