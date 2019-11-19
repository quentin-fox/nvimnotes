import pynvim
import subprocess
import uuid
import time
import re
from pathlib import Path

class Interface:

    def __init__(self, filename: str):
        f = Path(filename)
        if not f.exists():
            raise FileNotFoundError(f'{filename} could not be find in the working directory')
        elif f.suffix != '.pdf':
            raise OSError(f'{filename} is not a pdf file.')
        else:
            self.file = f
        self.server_code = str(uuid.uuid4()).replace('-', '')
        self._page_range = self._get_page_range()

    def _get_page_range(self):
        # uses pdfinfo since it's packaged with xpdf, no additional dependency
        pdf_info = subprocess.Popen(('pdfinfo', str(self.file)), stdout=subprocess.PIPE)
        pdf_info_stdout = pdf_info.communicate()[0]
        pdf_info_lst = pdf_info_stdout.decode('utf8').split('\n')
        pages = next((info for info in pdf_info_lst if "Pages" in info))
        page_int = int(re.sub(r'.*:\D*', '', pages)) # matches any non-digits
        return range(1, page_int + 1)

    def _send_command(self, command: str):
        args = (
            'xpdf',
            '-remote',
            str(self.server_code),
            command,
        )
        process = subprocess.Popen(args, stderr=subprocess.DEVNULL)
        return process

    def open(self):
        filename = str(self.file)
        start_cmds = [
            f'openFile({filename})',
            'singlePageMode',
            'closeSidebar',
            'zoomFitWidth'
        ]

        for i, cmd in enumerate(start_cmds):
            self._send_command(cmd)
            if i == 0:
                time.sleep(1.5)
            else:
                time.sleep(0.25)
        self._current_page = 1

    @property
    def current_page(self):
        return self._current_page

    @current_page.setter
    def current_page(self, page: int):
        if not isinstance(page, int):
            raise TypeError(f'Page number must be an integer')
        elif page not in self._page_range:
            raise IndexError(f'Page number must be between 1 and {max(self._page_range)}')
        else:
            self._send_command(f'gotoPage({page})')
            self._current_page = page

    def next_page(self):
        self._send_command('nextPage')
        if self._current_page + 1 in self._page_range:
            self._current_page += 1

    def prev_page(self):
        if self._current_page - 1 in self._page_range:
            self._current_page -= 1

    def quit(self):
        self._send_command('quit')







if __name__ == '__main__':
    i = Interface('test.pdf')
    i.open()


