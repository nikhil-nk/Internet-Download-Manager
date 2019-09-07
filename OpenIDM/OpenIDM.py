import os
import sys
import time
from queue import Queue
from threading import Thread
import requests as req

# Default Values
byte_size = 1048576
max_threads = 5
max_retry = 5
default_path = os.path.join(os.environ["HOME"], 'Downloads', 'OpenIDM')
footer_size = 22  # The size of the data proves the file was downloaded by this script
footer_indicator = "fuz_file"

# Base directory insurance
if not os.path.exists(default_path): os.mkdir(default_path)


class File(object):
    """handles the information about the desired file"""

    def __init__(self, url=None, location=default_path, name=None):
        self.url = 'http://' + url if url and 'http' not in url else url
        self.name = self.url.split("/")[-1] if url and not name else name
        self._name = name
        self.location = location if os.path.isfile(location) or not self.name else os.path.join(location, self.name)
        self.name = self.location.split("/")[-1] if not self.name else self.name
        self.local_size = os.path.getsize(self.location)
        self.exists = self.check_existence()
        self.type = 'unknown'
        self.accept_range = False
        self.size = None
        self.online = self.grab_data()

    def grab_data(self):
        if self.url:
            try:
                with req.get(self.url, stream=True) as con:
                    if "Accept-Ranges" in con.headers:
                        self.accept_range = True
                    else:
                        self.accept_range = False  # Check status_code for 206
                    self.size = int(con.headers['Content-length'])
                    self.type = con.headers['Content-Type'].split("/")[0]
                    return True
            except req.exceptions.ConnectionError as err:
                if self.exists:
                    return False
                raise Exception("Check your internet connection.")
        return False

    def check_existence(self):
        if os.path.exists(self.location) and os.path.isfile(self.location):
            return True
        else:
            if not self.url:
                raise Exception(
                    "No downloading resource, please enter one at least: \n- old interrupted download \n- file url")
            return False

    def __str__(self):
        if self.size:
            return f"{self.type} > {self.name} ({round(float(self.size) / byte_size, 2)}MB)"
        else:
            return f"Downloading {self.name}..."


class Download(object):
    """handles Downloading and ensure the file"""
    time_start = time.time()

    def __init__(self, file, threads=max_threads,
                 path=default_path, retries=max_retry, verbose=True, split=True):
        self.file = file
        self.path = path
        self.split = split
        self.verbose = verbose
        self.retries = retries
        self.download_location = os.path.join(self.path, self.file.name)
        self.threads_number = threads
        self.incomplete = []
        self.threads = []
        self.progress_list = []
        self.session = req.Session()
        self.chunk_list = Queue()
        self.order_list = Queue()
        self._extension = "fuz"
        self.__mine = self._check_my_download()
        self.chunk_size = int(self.file.size / len(str(self.file.size)))
        self.divisor = int(self.file.size / self.chunk_size)

        if self.file.size % self.chunk_size != 0:
            self.divisor = int(self.file.size / self.chunk_size) + 1

    def _check_my_download(self):  # Check the footer of the file
        try:
            if self.file.exists or os.path.exists(".".join([self.file.location, self._extension])):
                if not self.file.exists:
                    self.file.location = ".".join([self.file.location, self._extension])
                    self.file.local_size = os.path.getsize(self.file.location)
                with open(self.file.location, 'rb') as data:
                    data.seek(self.file.local_size - footer_size)
                    self.__footer = data.read(footer_size).decode()
                if footer_indicator in self.__footer:
                    old_size = int(self.__footer.split(" ")[-1])

                    if self.file.size:
                        if self.file.size != old_size:
                            raise Exception("The file in the url given is not the same as local file.")
                    else:
                        self.file.size = old_size

                    if self.file.location.split('.')[-1] != self._extension:
                        loc = ".".join([self.file.location, self._extension])
                        os.rename(self.file.location, loc)
                        self.file.location = loc

                    return True
                else:
                    if not self.file.online:
                        raise Exception("File is not supported and no given url.")
                    return False
        except UnicodeDecodeError:
            raise Exception(f"File Exists: the file {self.file.name} is already there {self.file.location}.")

    def chunk_distributor(self):  # Divide file size to chunks and loop count
        beg = 0
        if self.split:
            if self.incomplete:
                for chunk in range(len(self.incomplete)):
                    self.chunk_list.put(self.incomplete[chunk])
                    self.order_list.put(chunk)
            else:
                self.chunk_list.put(beg)
                for chunk in range(self.divisor):
                    if beg < self.file.size:
                        beg += self.chunk_size
                        self.chunk_list.put(beg)
                        self.order_list.put(chunk)
            self.thread_executor()
        else:
            if self.verbose:
                print("File Splitting is turned off...")
            self.normal_download()

    def normal_download(self):  # Downloading Chunks one-by-one
        payload = self.session.get(self.file.url, stream=True)
        with open(self.file.location, 'wb') as fil:
            for chunk in payload.iter_content(chunk_size=self.chunk_size):
                numb = self.progress_list[-1] if self.progress_list else 0
                self.progress(self.chunk_size + numb)
                if chunk:
                    fil.write(chunk)

    def get_chunk(self, start_byte, end_byte):  # Grabbing single chunk
        assert start_byte < end_byte
        assert start_byte < self.file.size
        if end_byte > self.file.size: end_byte = self.file.size
        bytes = "bytes={0}-{1}".format(start_byte, end_byte)
        for i in range(self.retries):
            try:
                chunk = self.session.get(self.file.url, headers={"Range": bytes}, stream=True)
                if chunk.status_code == 206: return chunk.content
            except Exception as err:
                print(f"Error: Could not download Chunk {start_byte}-{end_byte}",
                      ", Retrying..." if i < self.retries - 1 else "!")

    def chunk_collector(self):  # preparing for downloading chunk & writing data off
        try:
            while not self.order_list.empty():
                order = self.order_list.get()
                start = self.chunk_list.get()
                end = start + self.chunk_size - 1
                payload = self.get_chunk(start, end)
                with open(self.file.location, 'r+b') as writer:
                    writer.seek(start)
                    writer.write(payload)
                    self.progress(str(start))

                    writer.seek(0, 0)
                    writer.seek(self.file.size + 1)
                    writer.write(
                        f"{self.file.url};{self.file.name}|{';'.join(self.progress_list)}|fuz_file {self.file.size}".encode())
        except KeyboardInterrupt:
            print(" Closing...")
            exit()

    def thread_executor(self):  # Executing threads according to max_threads
        threads_needed = self.threads_number
        if self.threads_number > self.divisor:
            threads_needed = self.divisor

        for th in range(threads_needed):
            t = Thread(target=self.chunk_collector)
            t.start()
            self.threads.append(t)

    def wait_until(self, var1, var2, timeout=0, period=0.25):  # waits for certain condition
        wait = True
        mustend = time.time() + timeout
        while wait:
            if timeout != 0 and time.time() > mustend:
                wait = False
            if var1 in var2:
                return True
            time.sleep(period)
        return False

    def collect_data(self):
        beg = 0
        with open(self.file.location, 'rb') as fi:  # Read Text
            fi.seek(self.file.size + 1)
            data = fi.read().decode().split("|")

        old_url, old_name = data[0].split(';')
        done = data[1].split(';')
        for i in range(int(self.file.size / self.chunk_size) + 1):
            if beg < self.file.size:
                if str(beg) not in done:
                    self.incomplete.append(beg)
                beg += self.chunk_size
        self.divisor = len(self.incomplete)

        if self.file.online:
            if not self.file._name:
                self.file.name = old_name
        else:
            self.file.url = str(old_url)
            self.file.online = self.file.grab_data()

    def collect_file(self):  # Collecting downloaded data to one file
        if self.verbose:
            print("Collecting Downloaded Data...")
        if self.download_location.split('.')[-1] == self._extension:
            self.download_location = self.download_location.replace('.' + self._extension, '')
        with open(self.file.location, "rb") as inp:  # ger video data only
            file_data = inp.read(self.file.size)

        with open(self.download_location, 'wb') as out:  # Writes the video out
            out.write(file_data)

        os.remove(self.file.location)

    def progress(self, start):  # Recording progress& displaying
        self.progress_list.append(start)
        percent = round((len(self.progress_list) / self.divisor) * 100)
        if self.verbose:
            print(f"Downloading... {percent}%")
        if percent == 100:
            self.collect_file()
            if self.verbose:
                print("Downloaded in: {} Sec".format(round(time.time() - self.time_start, 2)))

    def download(self, auto=True):  # arranging and starting events
        try:
            if self.__mine:
                self.collect_data()
            else:
                if self.verbose:
                    print(self.file)
                if self.file.location.split('.')[-1] != self._extension:
                    self.file.location = ".".join([self.file.location, self._extension])
                with open(self.file.location, "wb") as f:
                    f.seek(self.file.size - 1)
                    f.write(b'\0')

            if self.file.online:
                status = self.session.get(self.file.url,
                                          headers={"Range": "bytes=0-1"}, stream=True).status_code

                if not self.file.accept_range and status != 206:
                    if self.verbose:
                        print("Server Doesn't Support File Splitting...")
                    self.split = False

                self.chunk_distributor()
            else:
                raise Exception("url given is not working.")
        except KeyboardInterrupt:
            print(" Closing...")
            exit()


def main():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("-u", "--url", help="URL of the file to download")
    parser.add_argument("-l", "--location", help="location of the file on machine")
    parser.add_argument("-n", "--name", help="Optional Custom name")
    parser.add_argument("-p", "--path", help="Change download directory path, Default: " + default_path)
    parser.add_argument("-r", "--retry", help="Set number of retries, default is " + str(max_retry))
    parser.add_argument("-s", "--no-split", action="store_true", help="Disable default file splitting behavior")
    parser.add_argument("-t", "--threads", help="Maximum number of threads to use (Working only if split is avilable)")
    parser.add_argument("-v", "--no-verbose", action="store_true",
                        help="Disable verbosity (Do not display output), default is Displaying")

    args = parser.parse_args()
    split = False if args.no_split else True
    verbose = False if args.no_verbos else True
    path = args.path if args.path else default_path
    location = args.location if args.location else default_path
    threads = args.threads if args.threads else max_threads
    retries = args.retry if args.retry else max_retry

    if len(sys.argv) > 1:
        Download(File(url=args.url, location=location, name=args.name), threads=threads, path=path, retries=retries,
                 verbose=verbose, split=split).download()
    else:
        parser.print_help(sys.stderr)


if __name__ == '__main__':
    main()
