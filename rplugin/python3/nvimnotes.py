import pynvim
import subprocess
import uuid
import time
import re
from pathlib import Path


@pynvim.plugin
class NvimNotes(object):

    def __init__(self, nvim):
        self.nvim = nvim

        # initialize settings from init.vim
        self._slide_section_str = self.nvim.eval('g:nvimnotes_slide_format')
        self._pdf_in_yaml = 1 == int(self.nvim.eval('g:nvimnotes_pdf_in_yaml'))
        if not self._pdf_in_yaml:
            self._pdf_section_str = self.nvim.eval('g:nvimnotes_pdf_section_format')

    def get_line(self, pattern: str, flags: str) -> int:
        # uses vim-style regex to search
        row, col = self.nvim.funcs.searchpos(pattern, flags)
        return (row - 1)

    def write_err(self, err: str):
        self.nvim.err_write(err + '\n')

    def write_msg(self, msg: str):
        self.nvim.msg_write(msg + '\n')

    @pynvim.command('Annotate', nargs='?')
    def annotate(self, args):
        """Search back for """
        if len(args) > 0:
            filename = args[0]
        else:
            filename = self.get_filename()
        try:
            self.interface = Interface(filename)
        except FileNotFoundError as err_fnf:
            self.write_err(str(err_fnf))
        except OSError as err_non_pdf:
            self.write_err(str(err_non_pdf))
        else:
            self.interface.open()

    def get_filename(self) -> str:
        buffer = self.nvim.current.buffer
        if self._pdf_in_yaml:
            pattern = r'^pdf: "?(.*pdf)"?$'
            pattern_vim = self.vimify_regex(pattern)
            yaml_pat = re.compile(pattern)

            file_ln = self.get_line(pattern_vim, 'bnc')
            file = buffer[file_ln]

            filename = yaml_pat.search(file).group(1)

        elif self._pdf_section_str:
            pattern_vim = self.vimify_regex(self._pdf_section_str)
            file_ln = self.get_line(pattern_vim)
            file = buffer[file_ln]
            section_pat = re.compile(self._pdf_section_str)
            filename = section_pat.search(file).group(1)
        return filename


    def vimify_regex(self, pattern: str) -> str:
        """Non-exhaustive function to convert python regex to vim regex"""
        newpat = pattern.replace('?', r'\=').replace('(', r'\)').replace(')', r'\)')
        return newpat



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


