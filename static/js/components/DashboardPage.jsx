import React from 'react';
import { useState, useEffect }from "react";

import LoadingSpinner from './LoadingSpinner';
import { useGlobalReducer } from '../contexts/GlobalContext';
import Select from 'react-select';

import ListAlerts from './ListAlerts';
import Aladin from './Aladin';

import Axios from 'axios';


const AppButton = ({ onPress, title }) => {
  return (
    <button onClick={onPress} style={styles.appButtonContainer}>
      <p style={styles.appButtonText}>{title}</p>
    </button>
  );
};

function Dashboard({navigation}) {
  //const db
  const [relatedSources, setRelateSources] = useState([]);
  const [telescopeName, setTelescopeName] = useState([]);
  const [eventId, setEventId] = useState([]);
  const [navigationID,setNavigationId]=useState(0)

  const [relatedTransients, setRelatedTransients] = useState([])
  //const [my_state, my_dispatch] = useGlobalReducer();

  useEffect(()=>{
    Axios.get('http://localhost:19007/api/get/id').then((response)=>{
      setEventId(response.data)
    })
  },[]);

  useEffect(()=>{
    Axios.get('http://localhost:19007/api/get/sources').then((response)=>{
      setRelateSources(response.data)
    })
  },[]);

  useEffect(()=>{
    Axios.get('http://localhost:19007/api/get/telescopes').then((response)=>{
      setTelescopeName(response.data)
    })
  },[]);

  useEffect(()=>{
    Axios.get('http://localhost:19007/api/get/transients_related').then((response)=>{
      setRelatedTransients(response.data)

      console.log('setRelatedTransients=>',response.data)
    })

  },[]);

  // const SubmitReview = () =>{
  //   Axios.post('http://localhost:19007/api/insert', {
  //     totoId: totoId,
  //     totoName: totoName,
  //   }).then(() => {
  //     alert("Succesful insert");
  //   })
  // }

  //revision slider
  const [value, setValue] = React.useState(30);
  const handleChange = (event, newValue) => {
    setValue(newValue);
  };

  //choice box telescope
  const telescopesOptions = telescopeName.map(telescope => ({
    value: telescope.name,
    label: telescope.name
  }));

  //choice box sources
  const sourcesOptions = relatedSources.map(source => ({
    value: source.name,
    label: source.name
  }));

  // Below is the skymap with basic setting hard coded to fix the initial display of the skymap.
  let fov = 180.0;
      

  let Skymap = <div style={{flex:1}}>
      <Aladin ra={13.623}
              dec={-23.8063}
              fov={fov}
              mode={'P/Mellinger/color'}/>
    </div>

  /*if (my_state.fetched_tca === "fetched") {
      renderPage = <div style={{flex:1}}>
          <Aladin ra={my_state.aladin_ra}
                  dec={my_state.aladin_dec}
                  fov={fov}
                  mode={my_state.aladin_mode}
                  tca={my_state.tca}
                  zadko={my_state.zadko}/>
      </div>
  } else {
      renderPage = <LoadingSpinner/>
  }*/

  console.log('relatedTransients =', relatedTransients)
  if(navigationID==1){
    return(
        <div>
          {Skymap}
          <AppButton
            title="Retour"
            onPress={() => {
              setNavigationId(0)
            }
          }/>
          <ListAlerts />
        </div>
    )
  }
  return (
    <div>
      {Skymap}
      {eventId.map((val)=> {
          return (<p style={styles.paragraph}>S190814bv - Campaign on going {"\n"}
          ID: {val.id}</p>)
        })}
      <p>Telescope Obs</p>
      <Select
            isMulti
            name="telescopes"
            options={telescopesOptions}
            className="basic-multi-select"
            classNamePrefix="select"
            menuPortalTarget={document.body}
          />
      <p>          Related Sources (eg. OTs) </p>
      <Select
            isMulti
            name="sources"
            options={sourcesOptions}
            className="basic-multi-select"
            classNamePrefix="select"
            menuPortalTarget={document.body}
          />
      {relatedTransients.map((val)=> {
          return (<p style={styles.text}>Transients: {val.alias}</p>)
        })}
      <AppButton
          title="List of alerts"
          onPress={() => {
            setNavigationId(1)
          }
        }/>
    </div>
  );
}

export default Dashboard

const styles = {
  container: {
    padding: 8,
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: '#cfe2f3ff',
  },
  paragraph: {
    margin: 18,
    marginTop: 30,
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  text: {
    fontSize: 16,
    textAlign: 'center',
    margin: 20,
  },
  multiselect: {
    marginLeft: 30,
    marginRight: 30,
    marginBottom: 0,
    marginTop: 0,
    padding: 20
  },
  item: {
    flex: 0.5,
    backgroundColor: 'white',
    borderWidth: 2,
    margin: 5,
  },
  card_skymap:{
    marginLeft: 30,
    marginRight: 30,
    marginBottom: 30,
    borderWidth: 2,
  },
  card:{
    marginLeft: 30,
    marginRight: 30,
    border: "none",
    boxShadow: "none"
  },
  card_info:{
    marginLeft: 30,
    marginRight: 30,
    marginTop: 90,
    borderWidth: 2,
  },
  appButtonContainer: {
    backgroundColor: '#ceccccff',
    borderRadius: 18,
    paddingVertical: 10,
    marginLeft: 90,
    marginRight: 90,
    marginBottom: 15,
  },
  appButtonText: {
    fontSize: 18,
    color: 'black',
    alignSelf: 'center',
  }
};
