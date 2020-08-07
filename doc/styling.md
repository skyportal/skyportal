# Styling components

SkyPortal is built on top of [Material UI](https://material-ui.com/)
(MUI).  We have evaluated several styling systems, including inline
styles, CSS Modules, and Styled Components, and have settled on using
[MUI's style hooks API](https://material-ui.com/styles/basics/#hook-api).

```js
import { makeStyles } from '@material-ui/core/styles';
```

MUI provides `makeStyles`, which takes in JSS (JavaScript Style
Sheets) and returns a CSS provider [hook](https://reactjs.org/docs/hooks-reference.html):

```js
const useStyles = makeStyles({
  root: {
    border: 0,
    padding: '1rem',
  },
});
```

The resulting `useStyles` can then be used inside of a component:

```jsx
import Button from '@material-ui/core/Button';

const MyButton = () => {
  const classes = useStyles();
  return <Button className={classes.root}>Click Me</Button>;
}
```

It is possible to make nested definitions:

```js
const useStyles = makeStyles({
  root: {
    color: 'red',
    '& p': {
      color: 'green',
      '& span': {
        color: 'blue'
      }
    }
  },
});
```

This is done via the
[`&` selector](http://lesscss.org/features/#parent-selectors-feature):
`&p` is a `p` element on `root` here.

You can also [parameterize `makeStyles`](https://material-ui.com/styles/basics/#adapting-based-on-props).

## Components

Please refer to the [MUI component
docs](https://material-ui.com/components/box/) for available
components and their props and CSS styles.

## Sizes

All sizes should be specified using `rem`, which stands for "root
element"—i.e., `1.5rem` would be 1.5 times the size of the font-size
specified in the root HTML element.

## Style props on Box

`makeStyles` is preferred in general, but for simple formatting you
may use [style
props](https://material-ui.com/system/basics/#all-inclusive) on `Box`
containers:

```
<Box m={2rem} />
```

See also "Grid system" below.

## Responsive Design

MUI uses
[breakpoints](https://material-ui.com/customization/breakpoints)
as a convenient way of writing CSS media queries.

Breakpoints understand the following pre-defined screen sizes:

- `xs` (extra-small): 0px or larger
- `sm` (small): 600px or larger
- `md` (medium): 960px or larger
- `lg` (large): 1280px or larger
- `xl` (extra-large): 1920px or larger

While MUI supports several breakpoint operators (`up`, `down`, `only`,
and `between`), because of confusing logic we only use `up`:

- `theme.breakpoints.up(sm)`: targets screen sizes `>= small`

Use it as follows:

```js
const useStyles = makeStyles({
  root: {
    backgroundColor: 'blue',
    [theme.breakpoints.up('md')]: {
      backgroundColor: 'red',
    },
  }
});
```

You may customize media-queries using the
[`useMediaQuery`](https://material-ui.com/components/use-media-query)
hook.

### Grid system

For positioning components on a page, MUI provides a [12-column grid
layout](https://material-ui.com/components/grid/).

There are two `Grid` types: `container` (outer element) and `item`
(inner elements).

```jsx
<Grid container spacing={1rem}>
  <Grid item xs={4}>
    <Paper>Cell 1</Paper>
  </Grid>
  <Grid item xs={4}>
    <Paper>Cell 2</Paper>
  </Grid>
  <Grid item xs={4}>
    <Paper>Cell 3</Paper>
</Grid>
```

The `xs` above refers to `xs`, the breakpoint from the previous
section.  In other words, this split of cells will be used from `xs`
and up.
[Multiple breakpoints](https://material-ui.com/components/grid/#grid-with-breakpoints)
can be specified.

You can also leave the value of `xs` blank, in which case elements are automatically spaced:

```jsx
<Grid container spacing={1rem}>
  <Grid item xs>
    <Paper>Cell 1</Paper>
  </Grid>
  <Grid item xs={6}>
    <Paper>Cell 2</Paper>
  </Grid>
  <Grid item xs>
    <Paper>Cell 3</Paper>
</Grid>
```

## Do's and don'ts

- Do not use inline styles

  When a list of components are rendered with inline styles, you cannot
  easily use the web developer tools to modify all of their CSS at the
  same time (editing one will edit just one instance, instead of all).

  Inline styles are spread all over the place, so it is harder to
  hunt down.

  Inline CSS also does not support media queries for responsive design.
