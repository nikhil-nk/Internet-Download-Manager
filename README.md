# OpenIDM
A python based command-line tool to boost download speed using multiple concurrent threads.
Supports file chunking to bypass download limit imposed by ISP.

## Examples
Download a file:
`Download(File("URL")).download()`
Or using command-line
`OpenIDM -u URL`

Files are downloaded by default in `~/Downloads/OpenIDM`

Also you can continue downloading interrupted downloads:
```python
from OpenIDM import File, Download

file = File(location="PATH_TO_INCOMPLETE_DOWNLOAD_FILE (.part)")

down = Download(file)

down.download()
```

Or by command-line

`OpenIDM -l INCOMPLETE_DOWNLOAD_FILE.part`

You can also specify custom name or download path `-n NAME -p PATH`

## Command-line --help list

```bash
usage: OpenIDM.py [-h] [-u URL] [-l LOCATION] [-n NAME] [-p PATH] [-r RETRY] [-s] [-t THREADS] [-v] [-V] 

optional arguments:                                                 
    -h, --help                          show this help message and exit              
    -u URL, --url URL                   URL of the file to download                 
    -l LOCATION, --location LOCATION    location of the file on machine             
    -n NAME, --name NAME                Optional Custom name                        
    -p PATH, --path PATH                Change download directory path, Default: $HOME/Downloads/OpenIDM
    -r RETRY, --retry RETRY             Set max number of retries, default is 5          
    -s, --no-split                      Disable default file splitting behavior      
    -t THREADS, --threads THREADS       Maximum number of threads to use (Working only if split is avilable)                           
    -v, --no-verbos                     Disable verbosity (Do not display output), default is Displaying
    -V, --version                       Display tool version and exit
```
