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
          <Grid item xs={12} sm={6} md={4} lg={3} xl={2}>
            <SkyCam telescope={scope}/>
          </Grid>
        ))
      }
    </Grid>
  );
};


export default SkyCamPage;
