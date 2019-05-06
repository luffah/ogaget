# ogaget
Note: this tool is an alternative to the creation of collection in OGA and may not be adapted for all usage.

A tool to store credits related to media from OpenGameArt.org

# Usage
## Get all (credit file + media) in one command
```sh
# e.g. get/update some-title.txt (credit file) and some-title.ogg
./ogaget.py https://opengameart.org/content/some-title -dl
```
## Get the media later
```sh
# create a credit file from a media on OGA
./ogaget.py https://opengameart.org/content/some-title
# download the media (e.g. some-title.ogg)
./ogaget.py some-title.txt -dl
```


# About the credit file
The credit file format is completely unofficial.
It is a simple file storing entries `key: value`.

```
# commented line
a key: a value
an other key: value1; value2; value3

# values can be written on multiple lines
# beginning with a space
alterate key:
 value1; value2
 value3
```

By default, the `ogaget.py` store the following keys :
* title
* artist
* url artist
* url file
* url
* date
* license

# How it works ?
Values are collected by parsing HTTP responses (html) of the specified url with XML XPath.

# Timesheet of free software worker
- initial commit (conception & development) : 10 hours
- first debugging phase : 6 hours
