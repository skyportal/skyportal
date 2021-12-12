import * as React from 'react';
import { useState, useEffect }from "react";
import Axios from 'axios';

import PropTypes from 'prop-types';
import clsx from 'clsx';
import { makeStyles,withStyles } from '@mui/styles';

//import {lighten} from '@material-ui/core'

import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import MuiTableHead from "@mui/material/TableHead";
import TablePagination from '@mui/material/TablePagination';
import TableRow from '@mui/material/TableRow';
import TableSortLabel from '@mui/material/TableSortLabel';

import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
//import FormControlLabel from '@mui/material/FormControlLabel';
//import Switch from '@mui/material/Switch';
import DeleteIcon from '@mui/icons-material/Delete';
import FilterListIcon from '@mui/icons-material/FilterList';


const headCells = [
    { id: 'SourceID', numeric: true, disablePadding: true, label: 'Source ID' },
    { id: 'Name', numeric: false, disablePadding: true, label: 'Name' },
    { id: 'Groups', numeric: false, disablePadding: false, label: 'Groups' },
    { id: 'Time', numeric: false, disablePadding: false, label: 'Time' },
    { id: 'Distance', numeric: false, disablePadding: false, label: 'Distance' },
    { id: 'ErrorDistance', numeric: false, disablePadding: false, label: 'Err Distance' },
    { id: 'CurrentClassification', false: true, disablePadding: false, label: 'Current Classification' },
    { id: 'Rate', numeric: false, disablePadding: true, label: 'Rate' },
    { id: 'RelatedSources', false: true, disablePadding: false, label: 'Related Sources' },
    { id: 'View', numeric: false, disablePadding: false, label: 'View' },
    { id: 'Properties', numeric: false, disablePadding: false, label: 'Properties' },
    { id: 'favoritePersonalAction', numeric: false, disablePadding: false, label: 'Favorite Personal Action' },
];

const TableHeaderCell = withStyles((theme) => ({
  root: {
    color: "black",
    fontWeight: 'bold',
    fontSize: 18
  }
}))(TableCell);

const TableHead = withStyles((theme) => ({
  root: {
    backgroundColor: "#6485a2ff",
  }
}))(MuiTableHead);

function descendingComparator(a, b, orderBy) {
    if (b[orderBy] < a[orderBy]) {
      return -1;
    }
    if (b[orderBy] > a[orderBy]) {
      return 1;
    }
    return 0;
}

function getComparator(order, orderBy) {
    return order === 'desc'
      ? (a, b) => descendingComparator(a, b, orderBy)
      : (a, b) => -descendingComparator(a, b, orderBy);
}

function stableSort(array, comparator) {
    const stabilizedThis = array.map((el, index) => [el, index]);
    stabilizedThis.sort((a, b) => {
      const order = comparator(a[0], b[0]);
      if (order !== 0) return order;
      return a[1] - b[1];
    });
    return stabilizedThis.map((el) => el[0]);
}

function EnhancedTableHead(props) {
    const { classes, onSelectAllClick, order, orderBy, numSelected, rowCount, onRequestSort } = props;
    const createSortHandler = (property) => (event) => {
      onRequestSort(event, property);
    };

    return (
      <TableHead>
        <TableRow>
          {headCells.map((headCell) => (
            <TableHeaderCell
              key={headCell.id}
              align={'center'}
              padding={headCell.disablePadding ? 'none' : 'default'}
              sortDirection={orderBy === headCell.id ? order : false}
            >
              <TableSortLabel
                active={orderBy === headCell.id}
                direction={orderBy === headCell.id ? order : 'asc'}
                onClick={createSortHandler(headCell.id)}
              >
                {headCell.label}
                {orderBy === headCell.id ? (
                  <span className={classes.visuallyHidden}>
                    {order === 'desc' ? 'sorted descending' : 'sorted ascending'}
                  </span>
                ) : null}
              </TableSortLabel>
            </TableHeaderCell>
          ))}
        </TableRow>
      </TableHead>
    );
}


EnhancedTableHead.propTypes = {
    classes: PropTypes.object.isRequired,
    numSelected: PropTypes.number.isRequired,
    onRequestSort: PropTypes.func.isRequired,
    onSelectAllClick: PropTypes.func.isRequired,
    order: PropTypes.oneOf(['asc', 'desc']).isRequired,
    orderBy: PropTypes.string.isRequired,
    rowCount: PropTypes.number.isRequired,
};

const useToolbarStyles = makeStyles((theme) => ({
    root: {
    },
    highlight:null,
    title: {
      flex: '1 1 100%',
    },
}));

const EnhancedTableToolbar = (props) => {
    const classes = useToolbarStyles();
    const { numSelected } = props;

    return (
      <Toolbar
        className={clsx(classes.root, {
          [classes.highlight]: numSelected > 0,
        })}
      >
        {numSelected > 0 ? (
          <Typography className={classes.title} color="inherit" variant="subtitle1" component="div">
            {numSelected} selected
          </Typography>
        ) : (
          <Typography className={classes.title} variant="h6" id="tableTitle" component="div">

          </Typography>
        )}

        {numSelected > 0 ? (
          <Tooltip title="Delete">
            <IconButton aria-label="delete">
              <DeleteIcon />
            </IconButton>
          </Tooltip>
        ) : (
          <Tooltip title="Filter list">
            <IconButton aria-label="filter list">
              <FilterListIcon />
            </IconButton>
          </Tooltip>
        )}
      </Toolbar>
    );
  };

EnhancedTableToolbar.propTypes = {
    numSelected: PropTypes.number.isRequired,
};

export default function ListAlerts() {

    const classes = useStyles();
    const [order, setOrder] = React.useState('asc');
    const [orderBy, setOrderBy] = React.useState('calories');
    const [selected, setSelected] = React.useState([]);
    const [page, setPage] = React.useState(0);
    const [rowsPerPage, setRowsPerPage] = React.useState(10);

    const [transients, setTransients] = useState([]);
    
    useEffect(()=>{
      Axios.get('http://localhost:19007/api/get/transients').then((response)=>{
        setTransients(response.data)
      })
    },[]);
    console.log(transients);

    /*rows = {};
    for (e in transients){
      e.concat("View":"-", "Properties":"-", "Favorite Personal Action":"-")
    }*/
    const rows = transients;
    
    const handleRequestSort = (event, property) => {
      const isAsc = orderBy === property && order === 'asc';
      setOrder(isAsc ? 'desc' : 'asc');
      setOrderBy(property);
    };

    const handleSelectAllClick = (event) => {
      if (event.target.checked) {
        const newSelecteds = rows.map((n) => n.SourceID);
        setSelected(newSelecteds);
        return;
      }
      setSelected([]);
    };
    
    const handleClick = (event, SourceID) => {
      const selectedIndex = selected.indexOf(SourceID);
      let newSelected = [];
    
      if (selectedIndex === -1) {
        newSelected = newSelected.concat(selected, SourceID);
      } else if (selectedIndex === 0) {
        newSelected = newSelected.concat(selected.slice(1));
      } else if (selectedIndex === selected.length - 1) {
        newSelected = newSelected.concat(selected.slice(0, -1));
      } else if (selectedIndex > 0) {
        newSelected = newSelected.concat(
          selected.slice(0, selectedIndex),
          selected.slice(selectedIndex + 1),
        );
      }
    
      setSelected(newSelected);
    };

    const handleChangePage = (event, newPage) => {
      setPage(newPage);
    };
    
    const handleChangeRowsPerPage = (event) => {
        setRowsPerPage(parseInt(event.target.value, 10));
        setPage(0);
    };

    const isSelected = (SourceID) => selected.indexOf(SourceID) !== -1;
    
    const emptyRows = rowsPerPage - Math.min(rowsPerPage, rows.length - page * rowsPerPage);

    return (
      <div style={styles.container}>
        <div className={classes.root}>
          <Paper className={classes.paper}>
            <EnhancedTableToolbar numSelected={selected.length} />
            <TableContainer>
              <Table
                className={classes.table}
                aria-labelledby="tableTitle"
                size='small'
                aria-label="enhanced table"
              >
                <EnhancedTableHead
                  classes={classes}
                  numSelected={selected.length}
                  order={order}
                  orderBy={orderBy}
                  onSelectAllClick={handleSelectAllClick}
                  onRequestSort={handleRequestSort}
                  rowCount={rows.length}
                />
                <TableBody>
                  {stableSort(rows, getComparator(order, orderBy))
                    .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                    .map((row, index) => {
                      const isItemSelected = isSelected(row.SourceID);

                      return (
                        <TableRow
                          hover
                          onClick={(event) => handleClick(event, row.SourceID)}
                          aria-checked={isItemSelected}
                          tabIndex={-1}
                          key={row.SourceID}
                          selected={isItemSelected}
                        >

                          <TableCell component="th" scope="row" padding="none" align="center">
                            {row.SourceID}
                          </TableCell>
                          <TableCell align="center">{row.Name}</TableCell>
                          <TableCell align="center">{row.Groups}</TableCell>
                          <TableCell align="center">{row.Time}</TableCell>
                          <TableCell align="center">{row.Distance}</TableCell>
                          <TableCell align="center">{row.ErrorDistance}</TableCell>
                          <TableCell align="center">{row.CurrentClassification}</TableCell>
                          <TableCell align="center">{row.Rate}</TableCell>
                          <TableCell align="center">{row.RelatedSources}</TableCell>
                          <TableCell align="center">{row.View}</TableCell>
                        </TableRow>
                      );
                  })}
                  {emptyRows > 0 && (
                    <TableRow style={{ height: 33 * emptyRows }}>
                      <TableCell colSpan={6} />
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              rowsPerPageOptions={[5, 10, 25]}
              component="div"
              count={rows.length}
              rowsPerPage={rowsPerPage}
              page={page}
              onChangePage={handleChangePage}
              onChangeRowsPerPage={handleChangeRowsPerPage}
            />
          </Paper>
        </div>
      </div>
    );
}

const styles = {
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 5,
    paddingBottom: 5,
    padding: 0,
    marginLeft: 30,
    marginRight: 30,
  },
  text: {
    fontSize: 16,
    textAlign: 'center',
    margin: 2,
  },
  table: {
      minWidth: 650,
  },
  paragraph: {
    margin: 18,
    marginTop: 50,
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  head: {
    backgroundColor: 'black',
    color: 'white',
  },
};

const useStyles = makeStyles((theme) => ({
  root: {
    width: '100%',
    marginLeft: 30,
    marginRight: 30
  },
  paper: {
    width: '100%',
  },
  table: {
    minWidth: 750,
  },
  visuallyHidden: {
    border: 0,
    clip: 'rect(0 0 0 0)',
    height: 1,
    margin: -1,
    overflow: 'hidden',
    padding: 0,
    position: 'absolute',
    top: 20,
    width: 1,
  },
}));
