## How to build

### Dependencies

```
pip install sphinx sphinx-autobuild sphinx-autodoc-typehints sphinx-rtd-theme
```

### Build

Enter the `docs` directory and run:

```shell
update.bat
```

This is equivalent to:

```shell
sphinx-apidoc -o source ..
make html
```

### View

Open `docs/build/html/index.html` in your web browser.