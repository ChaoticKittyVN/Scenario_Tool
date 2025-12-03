## How to build

Enter the `docs` directory and run the following commands:

### Dependencies

```
pip install -r requirements.txt
```

### Build

Run:

```shell
# On Windows
build.bat

# On Linux/Mac
sh build.sh
# or
chmod +x build.sh
./build.sh
```

This is equivalent to:

```shell
sphinx-apidoc -o source ..
make html
```

### View

Open `docs/build/html/index.html` in your web browser.