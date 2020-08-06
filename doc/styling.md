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

## Size & Spacing

All sizes should be specified using `rem`, which stands for "root
element"—i.e., if you are specifying font size, `1.5rem` would be 1.5
times the size of the font-size specified in the root HTML element.



https://material-ui.com/system/spacing/

theme.spacing.unit(8) is the base unit for the layout grid

## Responsive Design

https://material-ui.com/customization/breakpoints/#theme-breakpoints-down-key-media-query

### Grid system:

https://material-ui.com/components/grid/
https://blog.logrocket.com/the-material-ui-grid-system/

### Using media queries directly:

https://material-ui.com/components/use-media-query/
https://stackoverflow.com/a/50780995/214686
https://material-ui.com/components/grid/

### Breakpoints

```
xs (extra-small): 0px or larger
sm (small): 600px or larger
md (medium): 960px or larger
lg (large): 1280px or larger
xl (extra-large): 1920px or larger
```

## Do's and don'ts

- Do not use inline styles

  When a list of components are rendered with inline styles, you cannot
  easily use the web developer tools to modify all of their CSS at the
  same time (editing one will edit just one instance, instead of all).

  Inline styles are spread all over the place, so it is harder to
  hunt down.

  Inline CSS also does not support media queries for responsive design.
